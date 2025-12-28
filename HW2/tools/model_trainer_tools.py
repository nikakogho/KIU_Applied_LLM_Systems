# tools/model_trainer_tools.py
from __future__ import annotations
import io
import sys
import traceback
from typing import Dict, Any

MODEL_TOOLS_SPEC = """
Model Tools (Agent C)

Tool: execute_python_code
- Request format:
  {"tool":"execute_python_code","args":{"code_string":"...python code..."}}
- Behavior:
  Executes the provided Python code and captures stdout/stderr.
- Output:
  {
    "action":"execute_python_code",
    "ok": true/false,
    "stdout": "...",
    "stderr": "...",
    "exception": "... optional ..."
  }

Guidance:
- Your generated code SHOULD print a final line:
  METRICS_JSON={...}
so that metrics are easy to parse.
""".strip()


def execute_python_code(code_string: str) -> Dict[str, Any]:
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout_buf, stderr_buf

    exc_text = None
    ok = True

    try:
        # Give code its own global namespace
        exec_globals: Dict[str, Any] = {"__name__": "__main__"}
        exec(code_string, exec_globals, None)
    except Exception:
        ok = False
        exc_text = traceback.format_exc()
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

    return {
        "action": "execute_python_code",
        "ok": ok,
        "stdout": stdout_buf.getvalue(),
        "stderr": stderr_buf.getvalue(),
        "exception": exc_text,
    }
