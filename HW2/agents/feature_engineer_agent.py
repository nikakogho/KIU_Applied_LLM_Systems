# agents/feature_engineer_agent.py
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from openai import OpenAI
from tools.feature_tools import (
    FEATURE_TOOLS_SPEC,
    create_interaction,
    encode_categorical,
    correlation_analysis,
    select_top_features,
)

AGENT_B_DESCRIPTION = """
You are Agent B: The Feature Engineer ("The Architect").

Goal:
- Maximize information density by creating useful new features and removing redundancy.
- You receive clean_data.csv and Agent A's summary.

Rules:
- You MUST be the one making semantic decisions (no hardcoded feature logic in Python).
- Add at least ONE new feature using create_interaction.
- Do feature selection (keep only most predictive features) using correlation_analysis + select_top_features.
- Output ONLY valid JSON with the required schema.
""".strip()

# B -> C handoff structure
@dataclass
class AgentBHandoff:
    engineered_data_path: str
    strategy_summary: str
    decisions: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]


class FeatureEngineerAgent:
    def __init__(
        self,
        model: str = "gpt-5",
        output_dir: str = "data",
        client: Optional[OpenAI] = None,
        max_llm_steps: int = 8,
        max_tool_requests_per_step: int = 12,
        log_events: bool = True,
    ) -> None:
        self.model = model
        self.output_dir = output_dir
        self.client = client or OpenAI()
        self.max_llm_steps = max_llm_steps
        self.max_tool_requests_per_step = max_tool_requests_per_step
        self.log_events = log_events

        self._logs: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []

    def _log(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if self.log_events:
            self._logs.append({"ts": time.time(), "event": event, "payload": payload or {}})

    def _ensure_output_dir(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)

    def _json_loads_safe(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def _system_prompt(self) -> str:
        return (
            AGENT_B_DESCRIPTION
            + "\n\n"
            + FEATURE_TOOLS_SPEC
            + "\n\n"
            + "Output ONLY JSON with schema:\n"
            + "{\n"
            + '  "tool_requests": [ {"tool": "...", "args": {...}}, ... ],\n'
            + '  "decisions": [ {...}, ... ],\n'
            + '  "strategy_summary": "short text summary",\n'
            + '  "final": true/false\n'
            + "}\n"
        )

    def _user_payload(
        self,
        clean_data_path: str,
        agent_a_summary: str,
        metadata: Dict[str, Any],
        head_rows: List[Dict[str, Any]],
        target: str,
        tool_results: List[Dict[str, Any]],
    ) -> str:
        return json.dumps(
            {
                "clean_data_path": clean_data_path,
                "agent_a_summary": agent_a_summary,
                "metadata": metadata,
                "head_rows": head_rows,
                "target": target,
                "recent_tool_results": tool_results,
                "instruction": (
                    "Propose next feature engineering actions. "
                    "You must create >= 1 interaction feature. "
                    "Then do correlation_analysis(target) and select_top_features(k). "
                    "Stop with final=true when engineered dataset is ready."
                ),
            },
            ensure_ascii=False,
        )

    def _execute_tool_requests(
        self, df: pd.DataFrame, tool_requests: List[Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        df_current = df
        results: List[Dict[str, Any]] = []
        tool_requests = tool_requests[: self.max_tool_requests_per_step]

        for req in tool_requests:
            tool = (req.get("tool") or "").strip()
            args = req.get("args") or {}
            self._log("tool_request", {"tool": tool, "args": args})

            try:
                if tool == "create_interaction":
                    df_current, info = create_interaction(df_current, args["expression"])
                    results.append({"tool": tool, "ok": True, "output": info})
                    self._decisions.append(info)

                elif tool == "encode_categorical":
                    df_current, info = encode_categorical(df_current, args["col"], args.get("method", "onehot"))
                    results.append({"tool": tool, "ok": True, "output": info})
                    self._decisions.append(info)

                elif tool == "correlation_analysis":
                    out = correlation_analysis(df_current, target=args["target"], top_n=int(args.get("top_n", 20)))
                    results.append({"tool": tool, "ok": True, "output": out})
                    self._decisions.append(out)

                elif tool == "select_top_features":
                    df_current, info = select_top_features(
                        df_current,
                        target=args["target"],
                        k=int(args["k"]),
                        keep_cols=args.get("keep_cols"),
                    )
                    results.append({"tool": tool, "ok": True, "output": info})
                    self._decisions.append(info)

                else:
                    results.append({"tool": tool, "ok": False, "error": "unknown_tool"})

            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                results.append({"tool": tool, "ok": False, "error": err})
                self._log("tool_error", {"tool": tool, "error": err})

        return df_current, results

    def run(self, clean_data_path: str, agent_a_summary: str, target: str, run_id: Optional[str] = None) -> AgentBHandoff:
        self._logs = []
        self._decisions = []

        df = pd.read_csv(clean_data_path)
        head_rows = df.head(5).to_dict(orient="records")
        metadata = {
            "shape": tuple(df.shape),
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "nunique": df.nunique(dropna=True).to_dict(),
            "null_counts": df.isna().sum().to_dict(),
        }

        tool_results: List[Dict[str, Any]] = []
        strategy_summary = ""

        for step in range(self.max_llm_steps):
            self._log("llm_step_start", {"step": step})

            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_payload(clean_data_path, agent_a_summary, metadata, head_rows, target, tool_results)},
                ],
            )

            raw = resp.output_text
            self._log("llm_raw_output", {"step": step, "text_head": raw[:1200]})

            try:
                plan = self._json_loads_safe(raw)
            except Exception:
                tool_results = [{"tool": "llm_output", "ok": False, "error": "Output must be ONLY valid JSON. Try again."}]
                continue

            if isinstance(plan.get("strategy_summary"), str) and plan["strategy_summary"].strip():
                strategy_summary = plan["strategy_summary"].strip()

            if isinstance(plan.get("decisions"), list):
                self._decisions.extend(plan["decisions"])

            tool_requests = plan.get("tool_requests") or []
            if not isinstance(tool_requests, list):
                tool_requests = []

            final = bool(plan.get("final", False))
            if final and len(tool_requests) == 0:
                break

            df, tool_results = self._execute_tool_requests(df, tool_requests)

            # refresh metadata after changes
            metadata["shape"] = tuple(df.shape)
            metadata["columns"] = list(df.columns)
            metadata["dtypes"] = {c: str(t) for c, t in df.dtypes.items()}
            metadata["nunique"] = df.nunique(dropna=True).to_dict()
            metadata["null_counts"] = df.isna().sum().to_dict()

        self._ensure_output_dir()
        out_path = os.path.join(self.output_dir, "engineered_data.csv" if not run_id else f"engineered_data_{run_id}.csv")
        df.to_csv(out_path, index=False)

        if not strategy_summary:
            strategy_summary = f"Engineered dataset saved to {out_path}. Final shape: {tuple(df.shape)}."

        return AgentBHandoff(
            engineered_data_path=out_path,
            strategy_summary=strategy_summary,
            decisions=self._decisions,
            logs=self._logs,
        )

    def run_as_dict(self, *args, **kwargs) -> Dict[str, Any]:
        return asdict(self.run(*args, **kwargs))
