# tests/test_agent_c.py
from pathlib import Path
import pandas as pd
import pytest
from agents.model_trainer_agent import ModelTrainerAgent
from tests.fakes import FakeOpenAI


def _write_engineered_csv(tmp_data_dir: Path) -> Path:
    # Minimal engineered dataset: numeric features + binary target
    df = pd.DataFrame(
        {
            "f1": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "f2": [1, 0, 1, 0, 1, 0],
            "Outcome": [0, 0, 1, 0, 1, 1],
        }
    )
    path = tmp_data_dir / "engineered_data.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_extract_metrics_parses_json_line(tmp_data_dir: Path):
    agent = ModelTrainerAgent(model="fake-model", client=FakeOpenAI([{"code_string": "", "decision": {"is_good_enough": True}, "notes": "", "final": True}]))

    stdout = "hello\nMETRICS_JSON={\"accuracy\":0.9,\"f1\":0.8}\n"
    metrics = agent._extract_metrics(stdout)
    assert metrics == {"accuracy": 0.9, "f1": 0.8}


def test_agent_c_one_shot_success(tmp_data_dir: Path):
    engineered_path = _write_engineered_csv(tmp_data_dir)

    # Code prints METRICS_JSON line. No external deps needed.
    code_ok = r"""
print("Training...")
print('METRICS_JSON={"accuracy": 0.75, "precision": 0.7, "recall": 0.6, "f1": 0.65}')
"""

    plan = {
        "code_string": code_ok,
        "decision": {"is_good_enough": True, "reason": "Meets baseline."},
        "notes": "One-shot.",
        "final": True,
    }

    agent = ModelTrainerAgent(
        model="fake-model",
        client=FakeOpenAI([plan]),
        max_attempts=5,
        log_events=True,
    )

    result = agent.run(
        engineered_data_path=str(engineered_path),
        agent_b_summary="engineered ok",
        target="Outcome",
    )

    assert result.final_metrics.get("accuracy") == 0.75
    assert "METRICS_JSON" in result.training_log
    assert len(result.decisions) == 1
    assert result.decisions[0]["exec_ok"] is True


def test_agent_c_recovers_after_exception_then_succeeds(tmp_data_dir: Path):
    engineered_path = _write_engineered_csv(tmp_data_dir)

    code_bad = r"""
print("Starting...")
raise ValueError("boom")
"""

    code_ok = r"""
print("Retrying with safer code...")
print('METRICS_JSON={"accuracy": 0.9, "precision": 0.9, "recall": 0.9, "f1": 0.9}')
"""

    plan1 = {
        "code_string": code_bad,
        "decision": {"is_good_enough": False, "reason": "Crashed, fix code."},
        "notes": "First attempt fails.",
        "final": False,
    }
    plan2 = {
        "code_string": code_ok,
        "decision": {"is_good_enough": True, "reason": "Now OK."},
        "notes": "Recovered.",
        "final": True,
    }

    agent = ModelTrainerAgent(
        model="fake-model",
        client=FakeOpenAI([plan1, plan2]),
        max_attempts=5,
        log_events=True,
    )

    result = agent.run(
        engineered_data_path=str(engineered_path),
        agent_b_summary="engineered ok",
        target="Outcome",
    )

    # should have 2 attempts
    assert len(result.decisions) == 2
    assert result.decisions[0]["exec_ok"] is False
    assert result.decisions[1]["exec_ok"] is True
    assert result.final_metrics.get("accuracy") == 0.9

    # training log should include exception text
    assert "ValueError" in result.training_log
    assert "boom" in result.training_log


def test_agent_c_stops_on_is_good_enough_even_if_final_false(tmp_data_dir: Path):
    engineered_path = _write_engineered_csv(tmp_data_dir)

    code_ok = r"""
print('METRICS_JSON={"accuracy": 0.8, "precision": 0.8, "recall": 0.8, "f1": 0.8}')
"""

    plan = {
        "code_string": code_ok,
        "decision": {"is_good_enough": True, "reason": "Good enough."},
        "notes": "final is false but should still stop",
        "final": False,
    }

    agent = ModelTrainerAgent(
        model="fake-model",
        client=FakeOpenAI([plan]),
        max_attempts=5,
        log_events=True,
    )

    result = agent.run(
        engineered_data_path=str(engineered_path),
        agent_b_summary="engineered ok",
        target="Outcome",
    )

    assert len(result.decisions) == 1
    assert result.final_metrics.get("f1") == 0.8
