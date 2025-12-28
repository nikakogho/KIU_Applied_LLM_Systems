# tests/test_agent_b.py
import pandas as pd
import pytest
from pathlib import Path

from agents.feature_engineer_agent import FeatureEngineerAgent
from tests.fakes import FakeOpenAI


def _make_clean_df():
    return pd.DataFrame(
        {
            "A": [1, 2, 3, 4, 5, 6, 7, 8],
            "B": [2, 3, 2, 5, 4, 7, 3, 6],
            "segment": ["x", "y", "z", "x", "y", "z", "x", "z"],
            "Outcome": [0, 1, 0, 1, 1, 0, 0, 1],
        }
    )



@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_agent_b_end_to_end_creates_engineered_csv(tmp_data_dir: Path):
    # Arrange
    clean_path = tmp_data_dir / "clean_data.csv"
    df = _make_clean_df()
    df.to_csv(clean_path, index=False)

    plan_step1 = {
        "tool_requests": [
            {"tool": "create_interaction", "args": {"expression": "A_over_B = A / B"}},
            {"tool": "encode_categorical", "args": {"col": "segment", "method": "onehot"}},
            {"tool": "correlation_analysis", "args": {"target": "Outcome", "top_n": 20}},
        ],
        "decisions": [{"note": "create interaction + encode + corr"}],
        "strategy_summary": "Step1 done",
        "final": False,
    }

    plan_step2 = {
        "tool_requests": [
            {"tool": "select_top_features", "args": {"target": "Outcome", "k": 3}}
        ],
        "decisions": [{"note": "selected top features"}],
        "strategy_summary": "Selected top features and saved engineered data.",
        "final": True,
    }

    fake_client = FakeOpenAI([plan_step1, plan_step2])

    agent = FeatureEngineerAgent(
        model="fake-model",
        output_dir=str(tmp_data_dir),
        client=fake_client,
        max_llm_steps=5,
    )

    # Act
    handoff = agent.run(
        clean_data_path=str(clean_path),
        agent_a_summary="cleaned ok",
        target="Outcome",
        run_id="test",
    )

    # Assert
    out_path = Path(handoff.engineered_data_path)
    assert out_path.exists()

    engineered = pd.read_csv(out_path)

    # Target must remain
    assert "Outcome" in engineered.columns

    # Tool execution records should be present
    created = [d for d in handoff.decisions if isinstance(d, dict) and d.get("action") == "create_interaction"]
    assert len(created) >= 1

    selected = [d for d in handoff.decisions if isinstance(d, dict) and d.get("action") == "select_top_features"]
    assert len(selected) >= 1

    # No missing values introduced (no division by zero in this dataset)
    assert engineered.isna().sum().sum() == 0


def test_agent_b_stops_when_final_and_no_tools(tmp_data_dir: Path):
    # Arrange
    clean_path = tmp_data_dir / "clean_data.csv"
    original_df = _make_clean_df()
    original_df.to_csv(clean_path, index=False)

    plan_final_immediate = {
        "tool_requests": [],
        "decisions": [],
        "strategy_summary": "Nothing to do.",
        "final": True,
    }

    fake_client = FakeOpenAI([plan_final_immediate])

    agent = FeatureEngineerAgent(
        model="fake-model",
        output_dir=str(tmp_data_dir),
        client=fake_client,
        max_llm_steps=5,
    )

    # Act
    handoff = agent.run(
        clean_data_path=str(clean_path),
        agent_a_summary="cleaned ok",
        target="Outcome",
        run_id="final",
    )

    # Assert
    out_path = Path(handoff.engineered_data_path)
    assert out_path.exists()

    engineered = pd.read_csv(out_path)
    assert engineered.shape == original_df.shape
    assert list(engineered.columns) == list(original_df.columns)


def test_agent_b_handles_bad_json_then_recovers(tmp_data_dir: Path):
    # Arrange
    clean_path = tmp_data_dir / "clean_data.csv"
    _make_clean_df().to_csv(clean_path, index=False)

    bad = "NOT JSON AT ALL"
    good = {
        "tool_requests": [
            {"tool": "create_interaction", "args": {"expression": "A_plus_B = A + B"}}
        ],
        "decisions": [{"note": "ok"}],
        "strategy_summary": "Recovered after bad json.",
        "final": True,
    }

    fake_client = FakeOpenAI([bad, good])

    agent = FeatureEngineerAgent(
        model="fake-model",
        output_dir=str(tmp_data_dir),
        client=fake_client,
        max_llm_steps=5,
    )

    # Act
    handoff = agent.run(
        clean_data_path=str(clean_path),
        agent_a_summary="cleaned ok",
        target="Outcome",
        run_id="recover",
    )

    # Assert
    out_path = Path(handoff.engineered_data_path)
    assert out_path.exists()

    engineered = pd.read_csv(out_path)
    assert "A_plus_B" in engineered.columns
