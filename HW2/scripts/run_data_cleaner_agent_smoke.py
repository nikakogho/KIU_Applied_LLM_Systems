import bootstrap # noqa: F401
import os
import pandas as pd
from agents.data_cleaner_agent import DataCleanerAgent

def main():
    # Tiny dataset designed to trigger imputation
    df = pd.DataFrame({
        "Age": [20, None, 40, None],
        "City": ["Tbilisi", "Kutaisi", None, "Batumi"],
        "Id": [101, 102, 103, 104],
    })
    os.makedirs("data", exist_ok=True)
    raw_path = "data/raw_smoke.csv"
    df.to_csv(raw_path, index=False)

    agent = DataCleanerAgent(model="gpt-5", output_dir="data")
    handoff = agent.run(raw_path, run_id="smoke")

    print("CLEAN:", handoff.clean_data_path)
    print("SUMMARY:", handoff.audit_summary)
    print("DECISIONS (first 5):", handoff.decisions[:5])
    print("LOG EVENTS:", len(handoff.logs))

    cleaned = pd.read_csv(handoff.clean_data_path)
    print("Cleaned shape:", cleaned.shape)
    print("Nulls after:\n", cleaned.isna().sum())

if __name__ == "__main__":
    main()
