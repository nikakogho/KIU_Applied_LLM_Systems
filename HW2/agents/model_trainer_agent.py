# agents/model_trainer_agent.py
from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from openai import OpenAI
from tools.model_trainer_tools import MODEL_TOOLS_SPEC, execute_python_code

AGENT_C_DESCRIPTION = """
You are Agent C: The Model Trainer ("The Coder").

Goal:
- Train a robust XGBoost model from engineered_data.csv.
- You must generate executable Python code and iterate based on results.

Critical requirement (feedback loop):
- Generate baseline code -> execute -> read metrics (Accuracy/Recall/F1) -> decide if good enough.
- If not good enough, modify hyperparameters and retry.
- Stop when good enough or when max attempts reached.

Rules:
- You MUST make the decisions; do not hardcode a fixed configuration in the orchestrator.
- Output ONLY valid JSON with the required schema.
""".strip()


@dataclass
class AgentCResult:
    final_metrics: Dict[str, Any]
    final_code: str
    training_log: str
    decisions: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]


class ModelTrainerAgent:
    def __init__(
        self,
        model: str = "gpt-5",
        client: Optional[OpenAI] = None,
        max_attempts: int = 7,
        log_events: bool = True,
    ) -> None:
        self.model = model
        self.client = client or OpenAI()
        self.max_attempts = max_attempts
        self.log_events = log_events
        self._logs: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []

    def _log(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        if self.log_events:
            self._logs.append({"ts": time.time(), "event": event, "payload": payload or {}})

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
            AGENT_C_DESCRIPTION
            + "\n\n"
            + MODEL_TOOLS_SPEC
            + "\n\n"
            + "Output ONLY JSON with schema:\n"
            + "{\n"
            + '  "code_string": "python code to run",\n'
            + '  "decision": {"is_good_enough": true/false, "reason": "..."},\n'
            + '  "notes": "short explanation",\n'
            + '  "final": true/false\n'
            + "}\n"
        )

    def _user_payload(
        self,
        engineered_data_path: str,
        agent_b_summary: str,
        target: str,
        attempt: int,
        last_exec: Optional[Dict[str, Any]],
    ) -> str:
        return json.dumps(
            {
                "engineered_data_path": engineered_data_path,
                "agent_b_summary": agent_b_summary,
                "target": target,
                "attempt": attempt,
                "last_execution": last_exec,
                "instruction": (
                    "Generate Python code that:\n"
                    "1) loads the CSV\n"
                    "2) splits train/test\n"
                    "3) trains an XGBoost classifier (or regressor if target looks continuous)\n"
                    "4) prints metrics and ends with: METRICS_JSON={...}\n"
                    "Use sklearn metrics: accuracy, precision, recall, f1 (for classification)."
                ),
            },
            ensure_ascii=False,
        )

    def _extract_metrics(self, stdout: str) -> Optional[Dict[str, Any]]:
        m = re.search(r"METRICS_JSON\s*=\s*(\{.*\})\s*$", stdout.strip(), flags=re.MULTILINE | re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None

    def run(self, engineered_data_path: str, agent_b_summary: str, target: str) -> AgentCResult:
        self._logs = []
        self._decisions = []

        last_exec: Optional[Dict[str, Any]] = None
        final_code = ""
        final_metrics: Dict[str, Any] = {}
        training_log_parts: List[str] = []

        for attempt in range(1, self.max_attempts + 1):
            self._log("attempt_start", {"attempt": attempt})

            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_payload(engineered_data_path, agent_b_summary, target, attempt, last_exec)},
                ],
            )

            raw = resp.output_text
            self._log("llm_raw_output", {"attempt": attempt, "text_head": raw[:1200]})

            plan = self._json_loads_safe(raw)
            code_string = plan.get("code_string", "")
            final_code = code_string

            exec_out = execute_python_code(code_string)
            last_exec = exec_out

            training_log_parts.append(f"\n--- Attempt {attempt} ---\n")
            training_log_parts.append(exec_out.get("stdout", ""))
            if exec_out.get("stderr"):
                training_log_parts.append("\n[stderr]\n" + exec_out["stderr"])
            if exec_out.get("exception"):
                training_log_parts.append("\n[exception]\n" + exec_out["exception"])

            metrics = self._extract_metrics(exec_out.get("stdout", ""))
            if metrics is not None:
                final_metrics = metrics

            decision = plan.get("decision") or {}
            self._decisions.append(
                {
                    "attempt": attempt,
                    "decision": decision,
                    "metrics": metrics,
                    "exec_ok": exec_out.get("ok"),
                }
            )

            if bool(plan.get("final", False)) or bool(decision.get("is_good_enough", False)):
                break

        return AgentCResult(
            final_metrics=final_metrics,
            final_code=final_code,
            training_log="".join(training_log_parts),
            decisions=self._decisions,
            logs=self._logs,
        )

    def run_as_dict(self, *args, **kwargs) -> Dict[str, Any]:
        return asdict(self.run(*args, **kwargs))
