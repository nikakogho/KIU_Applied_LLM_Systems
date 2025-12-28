from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional


class PipelineError(RuntimeError):
    pass


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_json(path: str, obj: Any) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _to_plain(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    return obj


class DataScienceTeam:
    """
    Orchestrates Agents A -> B -> C and persists artifacts under runs/<run_id>/.

    Expected agent interfaces:
      - agent_a.run(raw_data_path: str, target: str, **extra) -> dict-like or dataclass
      - agent_b.run(raw_data_path: str, target: str, agent_a_summary: str, **extra) -> dict-like
            must return: engineered_data_path: str
            should return: summary: str (or agent_b_summary)
      - agent_c.run(engineered_data_path: str, agent_b_summary: str, target: str) -> dict-like
            should return: final_metrics, final_code, training_log, decisions, logs
    """

    def __init__(
        self,
        agent_a: Any,
        agent_b: Any,
        agent_c: Any,
        runs_dir: str = "runs",
        copy_inputs: bool = True,
    ) -> None:
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.agent_c = agent_c
        self.runs_dir = runs_dir
        self.copy_inputs = copy_inputs

    def _new_run_id(self) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        return f"{ts}_{uuid.uuid4().hex[:8]}"

    def run(
        self,
        raw_data_path: str,
        target: str,
        run_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline and returns a small summary dict.
        Always writes intermediate artifacts after each stage completes.

        Returns:
          {
            "run_id": ...,
            "raw_data_path": ...,
            "engineered_data_path": ...,
            "target": ...,
            "final_metrics": {...},
            "status": "success" | "failed",
            "error": "... optional ..."
          }
        """
        extra = extra or {}
        run_id = run_id or self._new_run_id()

        run_root = os.path.join(self.runs_dir, run_id)
        d_inputs = os.path.join(run_root, "00_inputs")
        d_a = os.path.join(run_root, "10_agent_a")
        d_b = os.path.join(run_root, "20_agent_b")
        d_c = os.path.join(run_root, "30_agent_c")
        d_final = os.path.join(run_root, "99_final")

        for d in (d_inputs, d_a, d_b, d_c, d_final):
            _ensure_dir(d)

        summary: Dict[str, Any] = {
            "run_id": run_id,
            "raw_data_path": raw_data_path,
            "engineered_data_path": None,
            "target": target,
            "final_metrics": {},
            "status": "failed",
        }

        # Snapshot inputs metadata
        input_meta = {
            "run_id": run_id,
            "raw_data_path": raw_data_path,
            "target": target,
            "started_at_unix": time.time(),
            "extra": extra,
        }
        _write_json(os.path.join(d_inputs, "input_meta.json"), input_meta)

        if self.copy_inputs:
            try:
                shutil.copy2(raw_data_path, os.path.join(d_inputs, os.path.basename(raw_data_path)))
            except Exception:
                # input might be huge or missing in tests; best effort
                pass

        try:
            # Agent A
            t0 = time.time()
            a_res = self.agent_a.run(raw_data_path=raw_data_path, target=target, **extra)
            a_plain = _to_plain(a_res)
            _write_json(os.path.join(d_a, "agent_a_result.json"), a_plain)
            _write_json(os.path.join(d_a, "timing.json"), {"seconds": time.time() - t0})

            agent_a_summary = ""
            if isinstance(a_plain, dict):
                agent_a_summary = a_plain.get("summary") or ""
            if not agent_a_summary:
                # fall back to a compact string version
                agent_a_summary = json.dumps(a_plain, ensure_ascii=False)[:6000]

            # Agent B
            t0 = time.time()
            b_res = self.agent_b.run(
                raw_data_path=raw_data_path,
                target=target,
                agent_a_summary=agent_a_summary,
                **extra,
            )
            b_plain = _to_plain(b_res)
            _write_json(os.path.join(d_b, "agent_b_result.json"), b_plain)
            _write_json(os.path.join(d_b, "timing.json"), {"seconds": time.time() - t0})

            if not isinstance(b_plain, dict):
                raise PipelineError("Agent B must return a dict-like object including engineered_data_path")

            engineered_data_path = b_plain.get("engineered_data_path")
            if not engineered_data_path or not isinstance(engineered_data_path, str):
                raise PipelineError("Agent B did not return engineered_data_path (string)")

            agent_b_summary = (
                b_plain.get("summary")
                or b_plain.get("agent_b_summary")
                or "(no agent_b_summary provided)"
            )

            summary["engineered_data_path"] = engineered_data_path

            # Snapshot engineered csv into run folder (best effort)
            try:
                shutil.copy2(engineered_data_path, os.path.join(d_b, os.path.basename(engineered_data_path)))
            except Exception:
                pass

            # Agent C
            t0 = time.time()
            c_res = self.agent_c.run(
                engineered_data_path=engineered_data_path,
                agent_b_summary=agent_b_summary,
                target=target,
            )
            c_plain = _to_plain(c_res)
            _write_json(os.path.join(d_c, "agent_c_result.json"), c_plain)
            _write_json(os.path.join(d_c, "timing.json"), {"seconds": time.time() - t0})

            # Convenience outputs
            if isinstance(c_plain, dict):
                final_code = c_plain.get("final_code") or ""
                training_log = c_plain.get("training_log") or ""
                final_metrics = c_plain.get("final_metrics") or {}

                if final_code:
                    with open(os.path.join(d_c, "final_code.py"), "w", encoding="utf-8") as f:
                        f.write(final_code)

                if training_log:
                    with open(os.path.join(d_c, "training_log.txt"), "w", encoding="utf-8") as f:
                        f.write(training_log)

                summary["final_metrics"] = final_metrics

            # Final bundle
            summary["status"] = "success"
            summary["finished_at_unix"] = time.time()

            _write_json(os.path.join(run_root, "run_summary.json"), summary)
            _write_json(
                os.path.join(d_final, "final.json"),
                {"agent_a": a_plain, "agent_b": b_plain, "agent_c": c_plain, "summary": summary},
            )

            return summary

        except Exception as e:
            summary["error"] = f"{type(e).__name__}: {e}"
            summary["finished_at_unix"] = time.time()
            _write_json(os.path.join(run_root, "run_summary.json"), summary)
            _write_json(os.path.join(d_final, "final.json"), {"summary": summary})
            raise
