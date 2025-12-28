import os
import pandas as pd
import bootstrap # noqa: F401
from agents.data_cleaner_agent import DataCleanerAgent

def main():
    df = pd.DataFrame({
        "Outcome": [1, 0, 1, 0, 1],
        "SomeID": [10, 11, 12, 13, 14],
        "x": [1.0, None, 2.0, None, 3.0],
    })
    os.makedirs("data", exist_ok=True)
    raw_path = "data/raw_feedback.csv"
    df.to_csv(raw_path, index=False)

    agent = DataCleanerAgent(model="gpt-5", output_dir="data")

    feedback = "Do NOT drop column 'Outcome' under any circumstances."
    handoff = agent.run(raw_path, run_id="feedback", feedback=feedback)

    cleaned = pd.read_csv(handoff.clean_data_path)

    print("Columns after:", list(cleaned.columns))
    assert "Outcome" in cleaned.columns, "Outcome was dropped despite feedback!"
    print("OK: Outcome preserved.")
    print("Summary:\n", handoff.audit_summary)

    steps = [e for e in handoff.logs if e["event"] == "llm_step_start"]
    tools = [e for e in handoff.logs if e["event"] == "tool_request"]
    print("LLM steps:", len(steps))
    print("Tool calls:", len(tools))


if __name__ == "__main__":
    main()
