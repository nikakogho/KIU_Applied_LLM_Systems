import os
import pandas as pd
import bootstrap  # noqa: F401
from agents.model_trainer_agent import ModelTrainerAgent
import numpy as np

def generate_data():
    rng = np.random.default_rng(42)
    n = 200

    df = pd.DataFrame({
        # Core signal features
        "age": rng.integers(18, 70, size=n),
        "income": rng.normal(50_000, 15_000, size=n).clip(20_000, 120_000),
        "tenure_years": rng.exponential(scale=5, size=n).clip(0, 30),

        # Binary / categorical-like
        "is_married": rng.integers(0, 2, size=n),
        "owns_house": rng.integers(0, 2, size=n),

        # Weakly informative numeric features
        "credit_score": rng.normal(650, 70, size=n).clip(300, 850),
        "num_children": rng.poisson(1.2, size=n),

        # Mostly noise (to prevent trivial learning)
        "noise_1": rng.normal(0, 1, size=n),
        "noise_2": rng.normal(0, 1, size=n),
    })

    # Construct a *soft* decision boundary
    logit = (
        0.03 * (df["age"] - 40)
        + 0.00004 * (df["income"] - 50_000)
        + 0.15 * df["owns_house"]
        + 0.10 * df["is_married"]
        + 0.08 * df["tenure_years"]
        + 0.002 * (df["credit_score"] - 650)
        - 0.05 * df["num_children"]
        + 0.1 * df["noise_1"]
    )

    prob = 1 / (1 + np.exp(-logit))

    df["Outcome"] = (rng.random(n) < prob).astype(int)

    engineered_path = "data/engineered_data_smoke_c.csv"
    df.to_csv(engineered_path, index=False)

    return engineered_path

def main():
    os.makedirs("data", exist_ok=True)

    engineered_path = generate_data()

    agent_c = ModelTrainerAgent(
        model="gpt-5",
        max_attempts=8,   # keep it bounded
        log_events=True,
    )

    result = agent_c.run(
        engineered_data_path=engineered_path,
        agent_b_summary="(smoke) features are numeric; train a simple baseline model.",
        target="Outcome",
    )

    # How many attempts did it actually do?
    attempts = len(result.decisions)

    print("ATTEMPTS:", attempts)
    print("FINAL METRICS:", result.final_metrics)
    print("DECISIONS:")
    for d in result.decisions:
        print(" -", d)

    # Sanity checks
    assert attempts >= 1
    assert isinstance(result.final_code, str) and len(result.final_code) > 0
    assert isinstance(result.training_log, str) and len(result.training_log) > 0

    # If metrics parsing worked, we should have something non-empty
    if result.final_metrics:
        print("Metrics parsed OK.")
    else:
        print("WARNING: No METRICS_JSON parsed. Check that model printed it.")

    # Helpful: show last 40 lines of stdout-ish log
    tail = result.training_log.splitlines()[-40:]
    print("\n--- TRAINING LOG TAIL ---")
    print("\n".join(tail))


if __name__ == "__main__":
    main()
