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
    Orchestrates your existing agents:

      A: DataCleanerAgent.run(raw_csv_path, feedback=None, previous_decisions=None, run_id=None) -> AgentAHandoff
      B: FeatureEngineerAgent.run(clean_data_path, agent_a_summary, target, run_id=None) -> AgentBHandoff
      C: ModelTrainerAgent.run(engineered_data_path, agent_b_summary, target) -> AgentCResult

    Persists artifacts under runs/<run_id>/.
    """

    def __init__(
        self,
        agent_a: Any,
        agent_b: Any,
        agent_c: Any,
        runs_dir: str = "runs",
        copy_inputs: bool = True,
        snapshot_intermediate_csvs: bool = True,
    ) -> None:
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.agent_c = agent_c
        self.runs_dir = runs_dir
        self.copy_inputs = copy_inputs
        self.snapshot_intermediate_csvs = snapshot_intermediate_csvs

    def _new_run_id(self) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        return f"{ts}_{uuid.uuid4().hex[:8]}"

    def run(
        self,
        raw_csv_path: str,
        target: str,
        run_id: Optional[str] = None,
        feedback: Optional[str] = None,
        previous_decisions: Optional[list[dict]] = None,
    ) -> Dict[str, Any]:
        """
        Returns a compact summary dict, and writes artifacts to runs/<run_id>/.

        summary = {
          "run_id": ...,
          "raw_csv_path": ...,
          "clean_data_path": ...,
          "engineered_data_path": ...,
          "target": ...,
          "final_metrics": {...},
          "status": "success"|"failed",
          "error": "... optional ..."
        }
        """
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
            "raw_csv_path": raw_csv_path,
            "clean_data_path": None,
            "engineered_data_path": None,
            "target": target,
            "final_metrics": {},
            "status": "failed",
        }

        # snapshot inputs metadata
        input_meta = {
            "run_id": run_id,
            "raw_csv_path": raw_csv_path,
            "target": target,
            "feedback": feedback,
            "started_at_unix": time.time(),
        }
        _write_json(os.path.join(d_inputs, "input_meta.json"), input_meta)

        if self.copy_inputs:
            try:
                shutil.copy2(raw_csv_path, os.path.join(d_inputs, os.path.basename(raw_csv_path)))
            except Exception:
                pass

        try:
            # -------------------------
            # Agent A: cleaning
            # -------------------------
            t0 = time.time()
            a_res = self.agent_a.run(
                raw_csv_path=raw_csv_path,
                feedback=feedback,
                previous_decisions=previous_decisions,
                run_id=run_id,
            )
            a_plain = _to_plain(a_res)
            _write_json(os.path.join(d_a, "agent_a_result.json"), a_plain)
            _write_json(os.path.join(d_a, "timing.json"), {"seconds": time.time() - t0})

            if not isinstance(a_plain, dict):
                raise PipelineError("Agent A must return a dict-like object (dataclass OK).")

            clean_data_path = a_plain.get("clean_data_path")
            agent_a_summary = a_plain.get("audit_summary")  # <-- correct field name

            if not clean_data_path or not isinstance(clean_data_path, str):
                raise PipelineError("Agent A did not return clean_data_path (string).")
            if not agent_a_summary or not isinstance(agent_a_summary, str):
                agent_a_summary = "(no audit_summary provided)"

            summary["clean_data_path"] = clean_data_path

            # snapshot clean csv into run folder (optional)
            if self.snapshot_intermediate_csvs:
                try:
                    shutil.copy2(clean_data_path, os.path.join(d_a, os.path.basename(clean_data_path)))
                except Exception:
                    pass

            # -------------------------
            # Agent B: feature engineering
            # -------------------------
            t0 = time.time()
            b_res = self.agent_b.run(
                clean_data_path=clean_data_path,
                agent_a_summary=agent_a_summary,
                target=target,
                run_id=run_id,
            )
            b_plain = _to_plain(b_res)
            _write_json(os.path.join(d_b, "agent_b_result.json"), b_plain)
            _write_json(os.path.join(d_b, "timing.json"), {"seconds": time.time() - t0})

            if not isinstance(b_plain, dict):
                raise PipelineError("Agent B must return a dict-like object (dataclass OK).")

            engineered_data_path = b_plain.get("engineered_data_path")
            agent_b_summary = b_plain.get("strategy_summary")  # <-- correct field name

            if not engineered_data_path or not isinstance(engineered_data_path, str):
                raise PipelineError("Agent B did not return engineered_data_path (string).")
            if not agent_b_summary or not isinstance(agent_b_summary, str):
                agent_b_summary = "(no strategy_summary provided)"

            summary["engineered_data_path"] = engineered_data_path

            # snapshot engineered csv into run folder (optional)
            if self.snapshot_intermediate_csvs:
                try:
                    shutil.copy2(engineered_data_path, os.path.join(d_b, os.path.basename(engineered_data_path)))
                except Exception:
                    pass

            # -------------------------
            # Agent C: model training
            # -------------------------
            t0 = time.time()
            c_res = self.agent_c.run(
                engineered_data_path=engineered_data_path,
                agent_b_summary=agent_b_summary,
                target=target,
            )
            c_plain = _to_plain(c_res)
            _write_json(os.path.join(d_c, "agent_c_result.json"), c_plain)
            _write_json(os.path.join(d_c, "timing.json"), {"seconds": time.time() - t0})

            if not isinstance(c_plain, dict):
                raise PipelineError("Agent C must return a dict-like object (dataclass OK).")

            final_metrics = c_plain.get("final_metrics") or {}
            summary["final_metrics"] = final_metrics

            if isinstance(final_metrics, dict) and final_metrics.get("error"):
                raise PipelineError(f"error: '{final_metrics.get('error')}'. Try again or check that your data is not garbage")

            # convenience outputs for quick debugging
            final_code = c_plain.get("final_code") or ""
            training_log = c_plain.get("training_log") or ""

            if final_code:
                with open(os.path.join(d_c, "final_code.py"), "w", encoding="utf-8") as f:
                    f.write(final_code)

            if training_log:
                with open(os.path.join(d_c, "training_log.txt"), "w", encoding="utf-8") as f:
                    f.write(training_log)

            # -------------------------
            # Final bundle
            # -------------------------
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
