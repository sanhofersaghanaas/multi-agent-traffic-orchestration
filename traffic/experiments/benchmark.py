"""
Benchmark & Evaluation Engine for Traffic Control Strategies
Runs comparative multi-seed experiments measuring waiting time, completion rate,
fairness max wait time, total network delay, and simulation duration.
"""

import time
import os
import pandas as pd
from config import BENCHMARK_SEEDS, DEFAULT_SIMULATION_STEPS, DATA_DIR
from agents.multi_agent_network import MultiAgentNetwork
from simulation.python_traffic_env import PythonTrafficEnv

STRATEGIES = [
    ("fixed_time", "Fixed-Time Control"),
    ("negotiated_directional", "Negotiated Directional"),
    ("fairness_aware", "Fairness-Aware Agentic (Proposed)")
]

def run_single_experiment(strategy_key, seed, sim_steps=DEFAULT_SIMULATION_STEPS):
    """
    Executes a single simulation run for given strategy and seed.
    """
    env = PythonTrafficEnv(seed=seed, max_steps=sim_steps)
    network = MultiAgentNetwork()
    
    obs = env.reset()
    start_time = time.time()

    for step in range(sim_steps):
        # 1. Update agent perceptions from environment observation
        network.update_agent_perceptions(obs)

        # 2. Get active actions per agent
        phase_actions = network.step_agents(strategy_key, step)

        # 3. Advance simulation step
        obs = env.step(phase_actions)

    elapsed_wall_time = time.time() - start_time
    metrics = env.get_summary_metrics()
    metrics["strategy_key"] = strategy_key
    metrics["seed"] = seed
    metrics["execution_time_sec"] = round(elapsed_wall_time, 3)

    return metrics

def run_full_benchmark(seeds=BENCHMARK_SEEDS, sim_steps=DEFAULT_SIMULATION_STEPS):
    """
    Runs multi-seed benchmark across all strategies and exports results to CSV.
    """
    results = []

    for strategy_key, strategy_name in STRATEGIES:
        for seed in seeds:
            m = run_single_experiment(strategy_key, seed, sim_steps=sim_steps)
            m["strategy_name"] = strategy_name
            results.append(m)

    df = pd.DataFrame(results)

    # Calculate summary metrics per strategy (averages across seeds)
    summary_df = df.groupby(["strategy_key", "strategy_name"]).agg({
        "avg_wait_time": "mean",
        "max_wait_time": "mean",
        "completion_rate": "mean",
        "total_delay": "mean",
        "execution_time_sec": "mean"
    }).reset_index()

    # Save to CSV
    csv_path = os.path.join(DATA_DIR, "benchmark_results.csv")
    df.to_csv(csv_path, index=False)

    return df, summary_df

if __name__ == "__main__":
    print("Running multi-seed traffic orchestration benchmark...")
    df, summary = run_full_benchmark()
    print("\n--- Benchmark Summary Results ---")
    print(summary.to_string(index=False))
