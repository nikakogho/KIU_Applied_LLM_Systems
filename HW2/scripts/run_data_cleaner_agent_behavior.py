import os
import pandas as pd
import bootstrap
from agents.data_cleaner_agent import DataCleanerAgent

def main():
    # ID column is unique per row -> reasonable to drop
    df = pd.DataFrame({
        "user_id": [f"U{i:04d}" for i in range(1, 51)],  # 50 unique strings
        "age": [20, None, 22, 23, None] * 10,
        "segment": ["A", "B", "A", None, "C"] * 10,
    })
    os.makedirs("data", exist_ok=True)
    raw_path = "data/raw_behavior.csv"
    df.to_csv(raw_path, index=False)

    agent = DataCleanerAgent(model="gpt-5", output_dir="data")
    handoff = agent.run(raw_path, run_id="behavior")

    cleaned = pd.read_csv(handoff.clean_data_path)

    print("Columns before:", list(df.columns))
    print("Columns after :", list(cleaned.columns))
    print("Nulls after:\n", cleaned.isna().sum())
    print("Summary:\n", handoff.audit_summary)

if __name__ == "__main__":
    main()
