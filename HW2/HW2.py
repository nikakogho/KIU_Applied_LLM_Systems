import argparse
from data_science_team import DataScienceTeam

from agents.data_cleaner_agent import DataCleanerAgent
from agents.feature_engineer_agent import FeatureEngineerAgent
from agents.model_trainer_agent import ModelTrainerAgent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True, help="Path to raw CSV")
    parser.add_argument("--target", required=True, help="Target column name")
    parser.add_argument("--run-id", default=None, help="Optional run id (folder name)")
    parser.add_argument("--runs-dir", default="runs", help="Where to store run artifacts")
    parser.add_argument("--feedback", default=None, help="Optional feedback string for Agent A")
    args = parser.parse_args()

    agent_a = DataCleanerAgent(model="gpt-5")
    agent_b = FeatureEngineerAgent(model="gpt-5")
    agent_c = ModelTrainerAgent(model="gpt-5", max_attempts=7, log_events=True)

    team = DataScienceTeam(
        agent_a=agent_a,
        agent_b=agent_b,
        agent_c=agent_c,
        runs_dir=args.runs_dir,
        copy_inputs=True,
        snapshot_intermediate_csvs=True,
    )

    summary = team.run(
        raw_csv_path=args.raw,
        target=args.target,
        run_id=args.run_id,
        feedback=args.feedback,
    )

    print("DONE. Summary:")
    print(summary)
    print(f"Artifacts saved in: {args.runs_dir}/{summary['run_id']}")


if __name__ == "__main__":
    main()
