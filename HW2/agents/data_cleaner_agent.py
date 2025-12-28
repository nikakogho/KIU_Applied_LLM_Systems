# agents/data_cleaner_agent.py
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from openai import OpenAI
from tools.cleaner_tools import (
    inspect_metadata,
    get_column_stats,
    impute_missing,
    drop_column,
)

# Handoff object A -> B
@dataclass
class AgentAHandoff:
    clean_data_path: str
    audit_summary: str
    decisions: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]

class DataCleanerAgent:
    """
    Agent A (Auditor/Cleaner):
      - Loads raw CSV
      - Uses tools: inspect_metadata, get_column_stats, impute_missing, drop_column
      - Writes cleaned CSV to output_dir/clean_data.csv (or run-specific name)
      - Produces a structured handoff for Agent B

    Design:
      - Orchestrator decides whether to re-run semantically.
      - This agent handles mechanical robustness (parsing, transient errors) locally.
    """

    def __init__(
        self,
        model: str = "gpt-5",
        output_dir: str = "data",
        client: Optional[OpenAI] = None,
        max_llm_steps: int = 6,
        log_events: bool = True,
    ) -> None:
        self.model = model
        self.output_dir = output_dir
        self.client = client or OpenAI()
        self.max_llm_steps = max_llm_steps
        self.log_events = log_events

        self._logs: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []

    def _log(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if not self.log_events:
            return
        self._logs.append(
            {"ts": time.time(), "event": event, "payload": payload or {}}
        )

    # Helpers
    def _ensure_output_dir(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)

    def _default_clean_path(self, run_id: Optional[str]) -> str:
        # Keep it predictable for grading, but allow per-run id if you want
        fname = "clean_data.csv" if not run_id else f"clean_data_{run_id}.csv"
        return os.path.join(self.output_dir, fname)

    def _json_loads_safe(self, text: str) -> Dict[str, Any]:
        """
        Robust-ish JSON extraction:
        - First try direct json.loads
        - Then try to locate the first {...} block
        """
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            # crude extraction of first JSON object
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def _system_prompt(self) -> str:
        return (
            "You are Agent A: a data auditor/cleaner.\n"
            "Goal: inspect a CSV dataframe, identify missingness / bad columns, and propose cleaning actions.\n"
            "You MUST output ONLY valid JSON with the schema described.\n\n"
            "You can request these tools by name (the orchestrator will execute them):\n"
            "- get_column_stats(col)\n"
            "- impute_missing(col, strategy) where strategy in {mean, median, mode}\n"
            "- drop_column(col)\n\n"
            "IMPORTANT:\n"
            "- Prefer minimal, reasonable cleaning.\n"
            "- Do not invent columns.\n"
            "- If feedback forbids an action, comply.\n\n"
            "JSON schema you must output:\n"
            "{\n"
            '  "tool_requests": [\n'
            "     {\"tool\": \"get_column_stats\", \"args\": {\"col\": \"...\"}},\n"
            "     {\"tool\": \"impute_missing\", \"args\": {\"col\": \"...\", \"strategy\": \"median\"}},\n"
            "     {\"tool\": \"drop_column\", \"args\": {\"col\": \"...\"}}\n"
            "  ],\n"
            '  "decisions": [\n'
            "     {\"action\": \"impute_missing\", \"col\": \"...\", \"strategy\": \"median\", \"reason\": \"...\"},\n"
            "     {\"action\": \"drop_column\", \"col\": \"...\", \"reason\": \"...\"}\n"
            "  ],\n"
            '  "audit_summary": \"short human-readable summary\",\n'
            '  "final": true/false\n'
            "}\n"
        )

    def _user_prompt(
        self,
        raw_csv_path: str,
        metadata: Dict[str, Any],
        feedback: Optional[str],
        previous_decisions: Optional[List[Dict[str, Any]]],
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        payload = {
            "raw_csv_path": raw_csv_path,
            "metadata": metadata,
            "feedback": feedback,
            "previous_decisions": previous_decisions or [],
            "recent_tool_results": tool_results or [],
            "instruction": (
                "Propose the next cleaning actions. "
                "If you need more info about a column, request get_column_stats first. "
                "If the dataset looks acceptable, set final=true."
            ),
        }
        return json.dumps(payload, ensure_ascii=False)

    def _execute_tool_requests(
        self, df: pd.DataFrame, tool_requests: List[Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Executes requested tools. Returns updated df and tool_results to show the LLM next step.
        """
        results: List[Dict[str, Any]] = []
        df_current = df

        for req in tool_requests:
            tool = (req.get("tool") or "").strip()
            args = req.get("args") or {}
            self._log("tool_request", {"tool": tool, "args": args})

            try:
                if tool == "get_column_stats":
                    col = args["col"]
                    out = get_column_stats(df_current, col)
                    results.append({"tool": tool, "args": args, "ok": True, "output": out})

                elif tool == "impute_missing":
                    col = args["col"]
                    strategy = args["strategy"]
                    df_current, info = impute_missing(df_current, col, strategy)
                    results.append({"tool": tool, "args": args, "ok": True, "output": info})

                    # record as a decision (if not already recorded by LLM)
                    self._decisions.append({**info, "action": "impute_missing"})

                elif tool == "drop_column":
                    col = args["col"]
                    df_current, info = drop_column(df_current, col)
                    results.append({"tool": tool, "args": args, "ok": True, "output": info})

                    self._decisions.append({**info, "action": "drop_column"})

                else:
                    results.append({"tool": tool, "args": args, "ok": False, "error": "unknown_tool"})

            except Exception as e:
                results.append({"tool": tool, "args": args, "ok": False, "error": f"{type(e).__name__}: {e}"})
                self._log("tool_error", {"tool": tool, "args": args, "error": f"{type(e).__name__}: {e}"})

        return df_current, results

    def run(
        self,
        raw_csv_path: str,
        feedback: Optional[str] = None,
        previous_decisions: Optional[List[Dict[str, Any]]] = None,
        run_id: Optional[str] = None,
    ) -> AgentAHandoff:
        self._logs = []
        self._decisions = []

        self._log(
            "agent_a_start",
            {
                "run_id": run_id,
                "raw_csv_path": raw_csv_path,
                "model": self.model,
                "feedback": feedback,
                "previous_decisions_count": 0 if previous_decisions is None else len(previous_decisions),
            },
        )

        # Load CSV
        try:
            df = pd.read_csv(raw_csv_path)
        except Exception as e:
            msg = f"Failed to read CSV at {raw_csv_path}: {type(e).__name__}: {e}"
            self._log("csv_read_error", {"error": msg})
            raise RuntimeError(msg) from e

        # Initial metadata
        metadata = inspect_metadata(df)
        self._log("inspect_metadata", {"summary": {"shape": metadata.get("shape")}})

        tool_results: List[Dict[str, Any]] = []

        # LLM loop: propose tools -> execute -> re-prompt until final
        audit_summary = ""
        for step in range(self.max_llm_steps):
            self._log("llm_step_start", {"step": step})

            user_prompt = self._user_prompt(
                raw_csv_path=raw_csv_path,
                metadata=metadata,
                feedback=feedback,
                previous_decisions=previous_decisions,
                tool_results=tool_results,
            )

            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = resp.output_text
            self._log("llm_raw_output", {"step": step, "text": text[:2000]})

            try:
                plan = self._json_loads_safe(text)
            except Exception as e:
                # Mechanical failure: retry locally by giving the model a correction hint once
                self._log("llm_parse_error", {"step": step, "error": f"{type(e).__name__}: {e}"})
                # On next iteration, tool_results includes the parse error (so model can fix formatting)
                tool_results = [{"tool": "llm_output", "ok": False, "error": "Output was not valid JSON. Output ONLY JSON."}]
                continue

            # capture audit summary & decisions
            audit_summary = plan.get("audit_summary") or audit_summary
            llm_decisions = plan.get("decisions") or []
            if isinstance(llm_decisions, list) and llm_decisions:
                self._decisions.extend(llm_decisions)

            # tool requests
            tool_requests = plan.get("tool_requests") or []
            if not isinstance(tool_requests, list):
                tool_requests = []

            df, tool_results = self._execute_tool_requests(df, tool_requests)

            # re-inspect metadata after changes
            metadata = inspect_metadata(df)

            final = bool(plan.get("final", False))
            self._log("llm_step_end", {"step": step, "final": final, "shape": metadata.get("shape")})
            if final:
                break

        # Save cleaned CSV
        self._ensure_output_dir()
        clean_data_path = self._default_clean_path(run_id)
        df.to_csv(clean_data_path, index=False)
        self._log("saved_clean_csv", {"clean_data_path": clean_data_path})

        # If model never wrote a summary, create a minimal one
        if not audit_summary:
            audit_summary = (
                f"Cleaned dataset saved to {clean_data_path}. "
                f"Final shape: {metadata.get('shape')}."
            )

        handoff = AgentAHandoff(
            clean_data_path=clean_data_path,
            audit_summary=audit_summary,
            decisions=self._decisions,
            logs=self._logs,
        )
        self._log("agent_a_end", {"run_id": run_id, "clean_data_path": clean_data_path})

        return handoff

    def run_as_dict(self, raw_csv_path: str, **kwargs) -> Dict[str, Any]:
        return asdict(self.run(raw_csv_path, **kwargs))
