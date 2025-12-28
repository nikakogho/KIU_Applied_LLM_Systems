import os
import pandas as pd
import bootstrap  # noqa: F401
from agents.feature_engineer_agent import FeatureEngineerAgent


def main():
    os.makedirs("data", exist_ok=True)

    # small clean dataset with a target
    df = pd.DataFrame(
        {
            "A": [1, 2, 3, 4, 5, 6, 7, 8],
            "B": [2, 3, 2, 5, 4, 7, 3, 6],
            "segment": ["x", "y", "z", "x", "y", "z", "x", "z"],
            "Outcome": [0, 1, 0, 1, 1, 0, 0, 1],
        }
    )

    clean_path = "data/clean_data_smoke_b.csv"
    df.to_csv(clean_path, index=False)

    agent_b = FeatureEngineerAgent(
        model="gpt-5",
        output_dir="data",
        max_llm_steps=4,  # keep it fast
    )

    handoff = agent_b.run(
        clean_data_path=clean_path,
        agent_a_summary="(smoke) dataset already clean",
        target="Outcome",
        run_id="smoke_b",
    )

    print("ENGINEERED:", handoff.engineered_data_path)
    print("SUMMARY:", handoff.strategy_summary)
    print("DECISIONS (first 8):")
    for d in handoff.decisions[:8]:
        print(" -", d)

    engineered = pd.read_csv(handoff.engineered_data_path)
    print("Shape:", engineered.shape)
    print("Columns:", list(engineered.columns))
    assert "Outcome" in engineered.columns, "Target column missing!"
    assert engineered.shape[0] == df.shape[0], "Row count changed unexpectedly!"

    # (Optional) quick sanity: should have >=1 new column at some point.
    # Not guaranteed to remain after select_top_features, so we check decisions.
    created = [x for x in handoff.decisions if isinstance(x, dict) and x.get("action") == "create_interaction"]
    if created:
        print("Created interaction:", created[0].get("new_col"))
    else:
        print("WARNING: No create_interaction recorded (check prompt / agent policy).")


if __name__ == "__main__":
    main()
