import os
import json
import shutil
import unittest
import pandas as pd

from data_science_team import DataScienceTeam


class FakeOpenAI:
    """
    Minimal fake client to simulate OpenAI usage.
    We just count calls and optionally return canned text.
    """
    def __init__(self):
        self.calls = []

    def call(self, who: str, payload: dict) -> dict:
        self.calls.append({"who": who, "payload": payload})
        return {"ok": True, "text": f"fake-response-from-{who}"}


class StubAgentA:
    def __init__(self, client: FakeOpenAI):
        self.client = client

    def run(self, raw_data_path: str, target: str, **extra):
        _ = self.client.call("agent_a", {"raw_data_path": raw_data_path, "target": target, "extra": extra})
        return {"summary": "A: inferred schema; suggest standard split; target is classification."}


class StubAgentB:
    def __init__(self, client: FakeOpenAI):
        self.client = client

    def run(self, raw_data_path: str, target: str, agent_a_summary: str, **extra):
        _ = self.client.call("agent_b", {"raw_data_path": raw_data_path, "target": target, "agent_a_summary": agent_a_summary})

        # Minimal "feature engineering": just load and re-save
        df = pd.read_csv(raw_data_path)
        engineered_path = os.path.join("data", "engineered_from_stub_b.csv")
        os.makedirs("data", exist_ok=True)
        df.to_csv(engineered_path, index=False)

        return {
            "engineered_data_path": engineered_path,
            "summary": "B: numeric features only; ready for XGBClassifier baseline."
        }


class StubAgentC:
    def __init__(self, client: FakeOpenAI):
        self.client = client

    def run(self, engineered_data_path: str, agent_b_summary: str, target: str):
        _ = self.client.call("agent_c", {"engineered_data_path": engineered_data_path, "agent_b_summary": agent_b_summary, "target": target})

        # Fake “training result”
        return {
            "final_metrics": {"task": "classification", "accuracy": 0.8, "f1": 0.78, "n_train": 100, "n_test": 50, "model": "XGBClassifier"},
            "final_code": "print('hello')\nprint('METRICS_JSON={\"f1\": 0.78}')\n",
            "training_log": "Attempt 1...\nMETRICS_JSON={\"f1\": 0.78}\n",
            "decisions": [{"attempt": 1, "decision": {"is_good_enough": True, "reason": "f1=0.78"}, "exec_ok": True}],
            "logs": [{"event": "attempt_start", "ts": 0}],
        }


class TestDataScienceTeam(unittest.TestCase):
    def setUp(self):
        # clean runs/ for test repeatability
        if os.path.isdir("runs"):
            shutil.rmtree("runs", ignore_errors=True)
        if os.path.isdir("data"):
            shutil.rmtree("data", ignore_errors=True)
        os.makedirs("data", exist_ok=True)

        # Create tiny raw dataset
        self.raw_path = os.path.join("data", "raw_test.csv")
        df = pd.DataFrame({
            "f1": [0.1, 0.2, 0.3, 0.4],
            "f2": [1, 0, 1, 0],
            "Outcome": [0, 0, 1, 1],
        })
        df.to_csv(self.raw_path, index=False)

    def test_orchestration_writes_artifacts_and_calls_fake_openai(self):
        client = FakeOpenAI()

        team = DataScienceTeam(
            agent_a=StubAgentA(client),
            agent_b=StubAgentB(client),
            agent_c=StubAgentC(client),
            runs_dir="runs",
            copy_inputs=True,
        )

        run_id = "unit_test_run"
        summary = team.run(raw_data_path=self.raw_path, target="Outcome", run_id=run_id)

        # 1) FakeOpenAI was “used”
        self.assertEqual(len(client.calls), 3)
        self.assertEqual([c["who"] for c in client.calls], ["agent_a", "agent_b", "agent_c"])

        # 2) Summary looks right
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["run_id"], run_id)
        self.assertIn("final_metrics", summary)
        self.assertGreaterEqual(summary["final_metrics"].get("f1", 0), 0.0)

        # 3) Artifacts exist
        run_root = os.path.join("runs", run_id)
        self.assertTrue(os.path.isfile(os.path.join(run_root, "run_summary.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "00_inputs", "input_meta.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "10_agent_a", "agent_a_result.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "20_agent_b", "agent_b_result.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "30_agent_c", "agent_c_result.json")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "30_agent_c", "final_code.py")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "30_agent_c", "training_log.txt")))
        self.assertTrue(os.path.isfile(os.path.join(run_root, "99_final", "final.json")))

        # 4) run_summary.json is valid JSON and matches returned summary
        with open(os.path.join(run_root, "run_summary.json"), "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["status"], "success")
        self.assertEqual(saved["run_id"], run_id)


if __name__ == "__main__":
    unittest.main()
