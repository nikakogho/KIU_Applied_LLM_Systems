import os
import json
import shutil
import unittest
import pandas as pd

from data_science_team import DataScienceTeam


class StubAgentA:
    """
    Matches DataCleanerAgent.run(raw_csv_path, feedback=None, previous_decisions=None, run_id=None)
    Returns dict with: clean_data_path, audit_summary, decisions, logs
    """
    def run(self, raw_csv_path: str, feedback=None, previous_decisions=None, run_id=None):
        os.makedirs("data", exist_ok=True)
        df = pd.read_csv(raw_csv_path)

        # pretend we cleaned: just re-save
        clean_path = os.path.join("data", f"clean_data_{run_id}.csv" if run_id else "clean_data.csv")
        df.to_csv(clean_path, index=False)

        return {
            "clean_data_path": clean_path,
            "audit_summary": "A: checked missingness; no major issues; saved cleaned CSV.",
            "decisions": [{"action": "noop", "reason": "data already clean in stub"}],
            "logs": [{"event": "agent_a_stub", "ok": True}],
        }


class StubAgentB:
    """
    Matches FeatureEngineerAgent.run(clean_data_path, agent_a_summary, target, run_id=None)
    Returns dict with: engineered_data_path, strategy_summary, decisions, logs
    """
    def run(self, clean_data_path: str, agent_a_summary: str, target: str, run_id=None):
        os.makedirs("data", exist_ok=True)
        df = pd.read_csv(clean_data_path)

        # add one simple engineered feature if possible
        cols = [c for c in df.columns if c != target]
        if len(cols) >= 2:
            df["interaction_stub"] = df[cols[0]] * df[cols[1]]
        else:
            df["interaction_stub"] = 0

        eng_path = os.path.join("data", f"engineered_data_{run_id}.csv" if run_id else "engineered_data.csv")
        df.to_csv(eng_path, index=False)

        return {
            "engineered_data_path": eng_path,
            "strategy_summary": "B: added one interaction feature; saved engineered CSV.",
            "decisions": [{"action": "create_interaction", "col": "interaction_stub"}],
            "logs": [{"event": "agent_b_stub", "ok": True}],
        }


class StubAgentC:
    """
    Matches ModelTrainerAgent.run(engineered_data_path, agent_b_summary, target)
    Returns dict with: final_metrics, final_code, training_log, decisions, logs
    """
    def run(self, engineered_data_path: str, agent_b_summary: str, target: str):
        # pretend we trained a model and got metrics
        return {
            "final_metrics": {"task": "classification", "accuracy": 0.8, "f1": 0.78, "n_train": 100, "n_test": 50, "model": "XGBClassifier"},
            "final_code": "print('training...')\nprint('METRICS_JSON={\"f1\": 0.78}')\n",
            "training_log": "Attempt 1...\nMETRICS_JSON={\"f1\": 0.78}\n",
            "decisions": [{"attempt": 1, "decision": {"is_good_enough": True, "reason": "f1=0.78"}}],
            "logs": [{"event": "agent_c_stub", "ok": True}],
        }


class TestDataScienceTeam(unittest.TestCase):
    def setUp(self):
        if os.path.isdir("runs"):
            shutil.rmtree("runs", ignore_errors=True)
        if os.path.isdir("data"):
            shutil.rmtree("data", ignore_errors=True)
        os.makedirs("data", exist_ok=True)

        self.raw_path = os.path.join("data", "raw_test.csv")
        df = pd.DataFrame(
            {
                "f1": [0.1, 0.2, 0.3, 0.4],
                "f2": [1, 0, 1, 0],
                "Outcome": [0, 0, 1, 1],
            }
        )
        df.to_csv(self.raw_path, index=False)

    def test_pipeline_success_and_artifacts(self):
        team = DataScienceTeam(
            agent_a=StubAgentA(),
            agent_b=StubAgentB(),
            agent_c=StubAgentC(),
            runs_dir="runs",
            copy_inputs=True,
            snapshot_intermediate_csvs=True,
        )

        run_id = "unit_test_run"
        summary = team.run(raw_csv_path=self.raw_path, target="Outcome", run_id=run_id, feedback=None)

        # Summary
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["run_id"], run_id)
        self.assertEqual(summary["raw_csv_path"], self.raw_path)
        self.assertEqual(summary["target"], "Outcome")
        self.assertTrue(isinstance(summary["final_metrics"], dict))
        self.assertIn("f1", summary["final_metrics"])

        # Artifacts
        run_root = os.path.join("runs", run_id)
        self.assertTrue(os.path.isfile(os.path.join(run_root, "run_summary.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "00_inputs", "input_meta.json")))

        self.assertTrue(os.path.isfile(os.path.join(run_root, "10_agent_a", "agent_a_result.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "20_agent_b", "agent_b_result.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "30_agent_c", "agent_c_result.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "30_agent_c", "final_code.py")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "30_agent_c", "training_log.txt")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "99_final", "final.json")))

        # run_summary.json matches
        with open(os.path.join(run_root, "run_summary.json"), "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["status"], "success")
        self.assertEqual(saved["run_id"], run_id)

        # Clean/engineered path should exist (produced by stubs)
        self.assertTrue(os.path.isfile(summary["clean_data_path"]))
        self.assertTrue(os.path.isfile(summary["engineered_data_path"]))

        # Optional snapshots in run folder (best-effort): assert they exist when copy works
        # clean snapshot
        clean_basename = os.path.basename(summary["clean_data_path"])
        self.assertTrue(os.path.isfile(os.path.join(run_root, "10_agent_a", clean_basename)))
        # engineered snapshot
        eng_basename = os.path.basename(summary["engineered_data_path"])
        self.assertTrue(os.path.isfile(os.path.join(run_root, "20_agent_b", eng_basename)))

    def test_pipeline_failure_writes_failed_summary(self):
        class FailingAgentB(StubAgentB):
            def run(self, *args, **kwargs):
                raise RuntimeError("boom")

        team = DataScienceTeam(
            agent_a=StubAgentA(),
            agent_b=FailingAgentB(),
            agent_c=StubAgentC(),
            runs_dir="runs",
            copy_inputs=True,
            snapshot_intermediate_csvs=True,
        )

        run_id = "unit_test_fail"
        with self.assertRaises(RuntimeError):
            team.run(raw_csv_path=self.raw_path, target="Outcome", run_id=run_id)

        run_root = os.path.join("runs", run_id)
        self.assertTrue(os.path.isfile(os.path.join(run_root, "run_summary.json")))
        with open(os.path.join(run_root, "run_summary.json"), "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["status"], "failed")
        self.assertIn("error", saved)


if __name__ == "__main__":
    unittest.main()
