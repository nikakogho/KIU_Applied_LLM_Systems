from __future__ import annotations

import io
import os
import sys
import time
import traceback
from typing import Dict, Any, Optional
import multiprocessing as mp
import uuid

MODEL_TOOLS_SPEC = """
Model Tools (Agent C)

Tool: execute_python_code
- Request format:
  {"tool":"execute_python_code","args":{"code_string":"...python code...", "timeout_seconds": 30}}

- Behavior:
  Executes the provided Python code in a separate process (hard-killable).
  Captures stdout/stderr and any exception traceback.

- Hard timeout:
  If execution exceeds timeout_seconds, the tool terminates the process and returns:
  exception = "TimeoutError: RESOURCE_GUARD_TRIGGERED (tool hard timeout after <N>s)"

- Output:
  {
    "action": "execute_python_code",
    "ok": true/false,
    "stdout": "...",
    "stderr": "...",
    "exception": "... optional ..."
  }

Guidance (required):
- Your generated code MUST print a final line exactly like:
  METRICS_JSON={...}
  so metrics are easy to parse.

- If you see last_execution.exception containing RESOURCE_GUARD_TRIGGERED:
  simplify the next attempt (use a faster approach, fewer heavy steps).
""".strip()

GENERATED_CODE_DIR = os.path.join("data", "agent_c_code")

def _save_code(code_string: str) -> Optional[str]:
    """
    Persist code_string to disk for debugging/repro.
    Returns the saved file path, or None if saving failed.
    """
    try:
        os.makedirs(GENERATED_CODE_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        uniq = uuid.uuid4().hex[:8]
        path = os.path.join(GENERATED_CODE_DIR, f"attempt_{ts}_{uniq}.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code_string)
        print('Wrote code at "', path, '"')
        return path
    except Exception:
        print("WARNING: Failed to save generated code for debugging.")
        exc_text = traceback.format_exc()
        print(exc_text)
        return None

def _exec_worker(code_string: str, q: mp.Queue) -> None:
    """
    Runs in a separate process so we can hard-timeout safely.
    Captures stdout/stderr and exception text.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout_buf, stderr_buf

    ok = True
    exc_text = None

    try:
        exec_globals: Dict[str, Any] = {"__name__": "__main__"}
        exec(code_string, exec_globals, None)
    except Exception:
        ok = False
        exc_text = traceback.format_exc()
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

    q.put(
        {
            "action": "execute_python_code",
            "ok": ok,
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "exception": exc_text,
        }
    )


def execute_python_code(code_string: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """
    Execute arbitrary Python code with a hard timeout.

    Why process-based?
    - `exec()` cannot be reliably interrupted in-process on Windows.
    - A separate process can be terminated if it hangs or overloads the machine.

    timeout_seconds defaults to 30s:
    - enough for a small XGBoost/Sklearn train+eval on a student laptop
    - prevents "freezing" if the model generates heavy code or infinite loops
    """
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        timeout_seconds = 30

    saved_code_path = _save_code(code_string)
    if saved_code_path:
        print(f"[DEBUG] Saved generated code to: {saved_code_path}")

    q: mp.Queue = mp.Queue()
    p = mp.Process(target=_exec_worker, args=(code_string, q), daemon=True)
    p.start()

    p.join(timeout_seconds)

    if p.is_alive():
        p.terminate()
        p.join(2)

        return {
            "action": "execute_python_code",
            "ok": False,
            "stdout": "",
            "stderr": "",
            "exception": (
                f"TimeoutError: RESOURCE_GUARD_TRIGGERED "
                f"(tool hard timeout after {timeout_seconds}s)"
            )
        }

    # Normal completion
    try:
        if not q.empty():
            return q.get_nowait()
    except Exception:
        pass

    # Should be rare (e.g., worker died before putting result)
    return {
        "action": "execute_python_code",
        "ok": False,
        "stdout": "",
        "stderr": "",
        "exception": "RuntimeError: Worker exited without returning output.",
    }
