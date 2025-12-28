from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
import tkinter as tk
from dataclasses import asdict, is_dataclass
from tkinter import filedialog, messagebox, ttk

from agents.data_cleaner_agent import DataCleanerAgent
from agents.feature_engineer_agent import FeatureEngineerAgent
from agents.model_trainer_agent import ModelTrainerAgent


# -------------------------
# Helpers for saving artifacts (same layout as DataScienceTeam)
# -------------------------

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _write_json(path: str, obj) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _to_plain(obj):
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def _open_folder(path: str) -> None:
    path = os.path.abspath(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def _new_run_id() -> str:
    import uuid
    ts = time.strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{uuid.uuid4().hex[:8]}"


# -------------------------
# GUI
# -------------------------

class _QueueWriter:
    """Redirect writes into a thread-safe queue for GUI display."""
    def __init__(self, q: "queue.Queue[str]", prefix: str = ""):
        self.q = q
        self.prefix = prefix

    def write(self, s: str) -> None:
        if s:
            self.q.put(self.prefix + s)

    def flush(self) -> None:
        pass


class DataScienceTeamGUI(tk.Tk):
    """
    GUI runner with:
      - per-agent progress messages
      - guaranteed DONE/FAILED message
      - heartbeat "still running..." every 5s
      - per-agent model selection dropdowns
    """

    # Weakest -> strongest (as requested)
    MODEL_OPTIONS = [
        "gpt-4o-mini",
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-5",
    ]

    def __init__(self):
        super().__init__()
        self.title("DataScienceTeam Runner")
        self.geometry("1020x780")

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self._running = False
        self._last_run_folder: str | None = None

        # Heartbeat state
        self._hb_stop = threading.Event()
        self._hb_thread: threading.Thread | None = None

        frm = tk.Frame(self, padx=10, pady=10)
        frm.pack(fill="x")

        tk.Label(frm, text="Raw CSV:").grid(row=0, column=0, sticky="w")
        self.raw_var = tk.StringVar(value="")
        tk.Entry(frm, textvariable=self.raw_var, width=80).grid(row=0, column=1, sticky="we", padx=(6, 6))
        tk.Button(frm, text="Browse…", command=self._browse_raw).grid(row=0, column=2, sticky="e")

        tk.Label(frm, text="Target column:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.target_var = tk.StringVar(value="Outcome")
        tk.Entry(frm, textvariable=self.target_var, width=30).grid(row=1, column=1, sticky="w", padx=(6, 6), pady=(8, 0))

        tk.Label(frm, text="Run ID (optional):").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.runid_var = tk.StringVar(value="")
        tk.Entry(frm, textvariable=self.runid_var, width=30).grid(row=2, column=1, sticky="w", padx=(6, 6), pady=(8, 0))

        tk.Label(frm, text="Runs dir:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.runsdir_var = tk.StringVar(value="runs")
        tk.Entry(frm, textvariable=self.runsdir_var, width=30).grid(row=3, column=1, sticky="w", padx=(6, 6), pady=(8, 0))

        tk.Label(frm, text="Feedback to Agent A (optional):").grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.feedback_var = tk.StringVar(value="")
        tk.Entry(frm, textvariable=self.feedback_var, width=80).grid(row=4, column=1, sticky="we", padx=(6, 6), pady=(8, 0))

        # -------------------------
        # Model selection (per agent)
        # -------------------------
        models_box = tk.LabelFrame(frm, text="OpenAI model per agent", padx=10, pady=8)
        models_box.grid(row=5, column=0, columnspan=3, sticky="we", pady=(12, 0))

        # defaults: A/B = 4o-mini, C = gpt-5
        self.model_a_var = tk.StringVar(value="gpt-4o-mini")
        self.model_b_var = tk.StringVar(value="gpt-4o-mini")
        self.model_c_var = tk.StringVar(value="gpt-5")

        tk.Label(models_box, text="Agent A (Cleaner):").grid(row=0, column=0, sticky="w")
        self.model_a_combo = ttk.Combobox(models_box, textvariable=self.model_a_var, values=self.MODEL_OPTIONS, state="readonly", width=18)
        self.model_a_combo.grid(row=0, column=1, sticky="w", padx=(8, 18))

        tk.Label(models_box, text="Agent B (Features):").grid(row=0, column=2, sticky="w")
        self.model_b_combo = ttk.Combobox(models_box, textvariable=self.model_b_var, values=self.MODEL_OPTIONS, state="readonly", width=18)
        self.model_b_combo.grid(row=0, column=3, sticky="w", padx=(8, 18))

        tk.Label(models_box, text="Agent C (Trainer):").grid(row=0, column=4, sticky="w")
        self.model_c_combo = ttk.Combobox(models_box, textvariable=self.model_c_var, values=self.MODEL_OPTIONS, state="readonly", width=18)
        self.model_c_combo.grid(row=0, column=5, sticky="w", padx=(8, 0))

        # small helper note
        tk.Label(
            models_box,
            text="Ordered weakest→strongest. Faster models help A/B a lot. C often benefits most from GPT-5.",
            fg="gray"
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

        # Buttons
        btn_row = tk.Frame(frm)
        btn_row.grid(row=6, column=0, columnspan=3, sticky="we", pady=(12, 0))

        self.run_btn = tk.Button(btn_row, text="Run pipeline", command=self._on_run_clicked)
        self.run_btn.pack(side="left")

        self.open_btn = tk.Button(btn_row, text="Open last run folder", command=self._open_last_folder, state="disabled")
        self.open_btn.pack(side="left", padx=(10, 0))

        self.clear_btn = tk.Button(btn_row, text="Clear log", command=self._clear_log)
        self.clear_btn.pack(side="left", padx=(10, 0))

        frm.grid_columnconfigure(1, weight=1)
        models_box.grid_columnconfigure(5, weight=1)

        # Log area
        log_frame = tk.Frame(self, padx=10, pady=10)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Log:").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=30, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        self.after(100, self._poll_log_queue)

    # -------------------------
    # UI plumbing
    # -------------------------

    def _browse_raw(self) -> None:
        path = filedialog.askopenfilename(
            title="Select raw CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.raw_var.set(path)

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", "end")

    def _append_log(self, s: str) -> None:
        self.log_text.insert("end", s)
        self.log_text.see("end")

    def _poll_log_queue(self) -> None:
        try:
            while True:
                s = self.log_queue.get_nowait()
                self._append_log(s)
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.run_btn.config(state=("disabled" if running else "normal"))
        # disable combos while running
        state = "disabled" if running else "readonly"
        self.model_a_combo.config(state=state)
        self.model_b_combo.config(state=state)
        self.model_c_combo.config(state=state)

    def _open_last_folder(self) -> None:
        if self._last_run_folder and os.path.isdir(self._last_run_folder):
            _open_folder(self._last_run_folder)
        else:
            messagebox.showinfo("No folder", "No run folder found yet.")

    # -------------------------
    # Heartbeat
    # -------------------------

    def _start_heartbeat(self) -> None:
        self._hb_stop.clear()

        def _hb():
            t0 = time.time()
            while not self._hb_stop.is_set():
                time.sleep(5)
                if self._hb_stop.is_set():
                    break
                elapsed = int(time.time() - t0)
                self.log_queue.put(f"[still running… {elapsed}s]\n")

        self._hb_thread = threading.Thread(target=_hb, daemon=True)
        self._hb_thread.start()

    def _stop_heartbeat(self) -> None:
        self._hb_stop.set()

    # -------------------------
    # Run handler
    # -------------------------

    def _on_run_clicked(self) -> None:
        if self._running:
            return

        raw = self.raw_var.get().strip()
        target = self.target_var.get().strip()
        run_id = self.runid_var.get().strip() or None
        runs_dir = self.runsdir_var.get().strip() or "runs"
        feedback = self.feedback_var.get().strip() or None

        # Model choices
        model_a = self.model_a_var.get().strip() or "gpt-4o-mini"
        model_b = self.model_b_var.get().strip() or "gpt-4o-mini"
        model_c = self.model_c_var.get().strip() or "gpt-5"

        if not raw:
            messagebox.showerror("Missing input", "Please select a raw CSV file.")
            return
        if not os.path.isfile(raw):
            messagebox.showerror("Bad path", f"File not found:\n{raw}")
            return
        if not target:
            messagebox.showerror("Missing input", "Please enter the target column name.")
            return

        if model_a not in self.MODEL_OPTIONS or model_b not in self.MODEL_OPTIONS or model_c not in self.MODEL_OPTIONS:
            messagebox.showerror("Bad model selection", "Selected model is not in the allowed options.")
            return

        self._set_running(True)
        self.open_btn.config(state="disabled")
        self._last_run_folder = None
        self._clear_log()

        self._append_log("=== Starting DataScienceTeam ===\n")
        self._append_log(f"raw_csv_path: {raw}\n")
        self._append_log(f"target: {target}\n")
        self._append_log(f"run_id: {run_id or '(auto)'}\n")
        self._append_log(f"runs_dir: {runs_dir}\n")
        self._append_log(f"feedback: {feedback or '(none)'}\n")
        self._append_log("\n--- Models ---\n")
        self._append_log(f"Agent A model: {model_a}\n")
        self._append_log(f"Agent B model: {model_b}\n")
        self._append_log(f"Agent C model: {model_c}\n\n")

        self._start_heartbeat()

        t = threading.Thread(
            target=self._run_pipeline_thread,
            args=(raw, target, run_id, runs_dir, feedback, model_a, model_b, model_c),
            daemon=True,
        )
        t.start()

    # -------------------------
    # Pipeline runner (per-agent progress + guaranteed DONE/FAILED)
    # -------------------------

    def _run_pipeline_thread(
        self,
        raw: str,
        target: str,
        run_id: str | None,
        runs_dir: str,
        feedback: str | None,
        model_a: str,
        model_b: str,
        model_c: str,
    ) -> None:
        # Redirect stdout/stderr from *this worker thread* to GUI
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = _QueueWriter(self.log_queue)
        sys.stderr = _QueueWriter(self.log_queue, prefix="[stderr] ")

        actual_run_id = run_id or _new_run_id()
        run_root = os.path.join(runs_dir, actual_run_id)
        d_inputs = os.path.join(run_root, "00_inputs")
        d_a = os.path.join(run_root, "10_agent_a")
        d_b = os.path.join(run_root, "20_agent_b")
        d_c = os.path.join(run_root, "30_agent_c")
        d_final = os.path.join(run_root, "99_final")
        for d in (d_inputs, d_a, d_b, d_c, d_final):
            _ensure_dir(d)

        summary = {
            "run_id": actual_run_id,
            "raw_csv_path": raw,
            "clean_data_path": None,
            "engineered_data_path": None,
            "target": target,
            "models": {"agent_a": model_a, "agent_b": model_b, "agent_c": model_c},
            "final_metrics": {},
            "status": "failed",
            "error": None,
        }

        def finalize_and_write(status: str, error: str | None) -> None:
            summary["status"] = status
            summary["error"] = error
            summary["finished_at_unix"] = time.time()
            _write_json(os.path.join(run_root, "run_summary.json"), summary)
            _write_json(os.path.join(d_final, "final.json"), {"summary": summary})

        try:
            # Input meta + snapshot
            _write_json(os.path.join(d_inputs, "input_meta.json"), {
                "run_id": actual_run_id,
                "raw_csv_path": raw,
                "target": target,
                "feedback": feedback,
                "models": summary["models"],
                "started_at_unix": time.time(),
            })
            try:
                shutil.copy2(raw, os.path.join(d_inputs, os.path.basename(raw)))
            except Exception:
                pass

            # Instantiate agents with selected models
            agent_a = DataCleanerAgent(model=model_a)
            agent_b = FeatureEngineerAgent(model=model_b)
            agent_c = ModelTrainerAgent(model=model_c, max_attempts=7, log_events=True)

            # ---------------- Agent A ----------------
            self.log_queue.put("\n--- Agent A: Data Cleaning (START) ---\n")
            self.log_queue.put(f"[Agent A model: {model_a}]\n")
            t0 = time.time()
            a_res = agent_a.run(
                raw_csv_path=raw,
                feedback=feedback,
                previous_decisions=None,
                run_id=actual_run_id,
            )
            a_plain = _to_plain(a_res) or {}
            _write_json(os.path.join(d_a, "agent_a_result.json"), a_plain)
            _write_json(os.path.join(d_a, "timing.json"), {"seconds": time.time() - t0})
            self.log_queue.put(f"--- Agent A: DONE ({time.time() - t0:.2f}s) ---\n")

            clean_data_path = (a_plain.get("clean_data_path") if isinstance(a_plain, dict) else None)
            agent_a_summary = (a_plain.get("audit_summary") if isinstance(a_plain, dict) else None) or "(no audit_summary)"

            if not clean_data_path or not isinstance(clean_data_path, str):
                raise RuntimeError("Agent A returned no clean_data_path (or wrong type).")

            summary["clean_data_path"] = clean_data_path

            # snapshot clean
            try:
                shutil.copy2(clean_data_path, os.path.join(d_a, os.path.basename(clean_data_path)))
            except Exception:
                pass

            # ---------------- Agent B ----------------
            self.log_queue.put("\n--- Agent B: Feature Engineering (START) ---\n")
            self.log_queue.put(f"[Agent B model: {model_b}]\n")
            t0 = time.time()
            b_res = agent_b.run(
                clean_data_path=clean_data_path,
                agent_a_summary=agent_a_summary,
                target=target,
                run_id=actual_run_id,
            )
            b_plain = _to_plain(b_res) or {}
            _write_json(os.path.join(d_b, "agent_b_result.json"), b_plain)
            _write_json(os.path.join(d_b, "timing.json"), {"seconds": time.time() - t0})
            self.log_queue.put(f"--- Agent B: DONE ({time.time() - t0:.2f}s) ---\n")

            engineered_data_path = (b_plain.get("engineered_data_path") if isinstance(b_plain, dict) else None)
            agent_b_summary = (b_plain.get("strategy_summary") if isinstance(b_plain, dict) else None) or "(no strategy_summary)"

            if not engineered_data_path or not isinstance(engineered_data_path, str):
                raise RuntimeError("Agent B returned no engineered_data_path (or wrong type).")

            summary["engineered_data_path"] = engineered_data_path

            # snapshot engineered
            try:
                shutil.copy2(engineered_data_path, os.path.join(d_b, os.path.basename(engineered_data_path)))
            except Exception:
                pass

            # ---------------- Agent C ----------------
            self.log_queue.put("\n--- Agent C: Model Training (START) ---\n")
            self.log_queue.put(f"[Agent C model: {model_c}]\n")
            t0 = time.time()
            c_res = agent_c.run(
                engineered_data_path=engineered_data_path,
                agent_b_summary=agent_b_summary,
                target=target,
            )
            c_plain = _to_plain(c_res) or {}
            _write_json(os.path.join(d_c, "agent_c_result.json"), c_plain)
            _write_json(os.path.join(d_c, "timing.json"), {"seconds": time.time() - t0})
            self.log_queue.put(f"--- Agent C: DONE ({time.time() - t0:.2f}s) ---\n")

            # Always write code/log if present (even if empty result)
            if isinstance(c_plain, dict):
                final_code = c_plain.get("final_code") or ""
                training_log = c_plain.get("training_log") or ""
                final_metrics = c_plain.get("final_metrics") or {}

                summary["final_metrics"] = final_metrics if isinstance(final_metrics, dict) else {}

                if isinstance(final_metrics, dict) and final_metrics.get("error"):
                    raise RuntimeError("Try again or check that your data is not utter garbage")

                with open(os.path.join(d_c, "final_code.py"), "w", encoding="utf-8") as f:
                    f.write(final_code or "# (empty final_code)\n")
                with open(os.path.join(d_c, "training_log.txt"), "w", encoding="utf-8") as f:
                    f.write(training_log or "(empty training_log)\n")
            else:
                with open(os.path.join(d_c, "final_code.py"), "w", encoding="utf-8") as f:
                    f.write("# (agent_c_result was not dict-like)\n")
                with open(os.path.join(d_c, "training_log.txt"), "w", encoding="utf-8") as f:
                    f.write("(agent_c_result was not dict-like)\n")

            # Final bundle
            summary["status"] = "success"
            summary["finished_at_unix"] = time.time()
            _write_json(os.path.join(run_root, "run_summary.json"), summary)
            _write_json(os.path.join(d_final, "final.json"), {"summary": summary})

            # Done message (guaranteed)
            self._last_run_folder = os.path.abspath(run_root)
            self.log_queue.put("\n=== DONE (pipeline finished) ===\n")
            self.log_queue.put(f"Status: {summary['status']}\n")
            self.log_queue.put(f"Run ID: {summary['run_id']}\n")
            self.log_queue.put(f"Artifacts: {self._last_run_folder}\n")
            self.log_queue.put(f"Final metrics: {summary.get('final_metrics')}\n")
            self.after(0, lambda: self.open_btn.config(state="normal"))

        except Exception:
            tb = traceback.format_exc()
            err = tb.splitlines()[-1] if tb else "Unknown error"
            finalize_and_write("failed", err)

            self._last_run_folder = os.path.abspath(run_root)
            self.log_queue.put("\n=== FAILED (pipeline ended with error) ===\n")
            self.log_queue.put(f"Artifacts: {self._last_run_folder}\n")
            self.log_queue.put(tb + "\n")
            self.after(0, lambda: messagebox.showerror("Pipeline failed", "See log for traceback."))
            self.after(0, lambda: self.open_btn.config(state="normal"))

        finally:
            self._stop_heartbeat()
            sys.stdout, sys.stderr = old_stdout, old_stderr
            self.after(0, lambda: self._set_running(False))


if __name__ == "__main__":
    app = DataScienceTeamGUI()
    app.mainloop()
