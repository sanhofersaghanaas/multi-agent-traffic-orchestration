"""
Benchmark Runner for P25 Multi-Modal Traffic Orchestration Network.
Executes systematic multi-seed evaluation comparing:
1. Fixed-Time Control (Baseline)
2. Negotiated Directional Control
3. Fairness-Aware Dynamic Control (Proposed)

Measures: Waiting time, Completion rate, Simulation duration, Starvation mitigation.
"""

import os
import sys
import json
import yaml
import pandas as pd
import numpy as np

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from simulation.env import TrafficEnvironment
from agents.coordinator import MultiAgentCoordinator

def run_single_simulation(strategy_type, seed, config=None, total_steps=360):
    """Executes a single simulation episode for a given strategy and seed."""
    env = TrafficEnvironment(config=config, seed=seed)
    env.metrics.strategy_name = strategy_type
    coordinator = MultiAgentCoordinator(strategy_type=strategy_type, config=config)
    
    done = False
    step = 0
    while not done and step < total_steps:
        # Agent coordination and phase selection
        coordinator.step(env)
        # Environment simulation step
        _, done, metrics = env.step()
        step += 1
        
    summary = env.metrics.get_summary()
    env.close()
    return summary, env.metrics

def run_full_benchmark(seeds=None, total_steps=360, config_path=None, output_dir=None):
    """Runs the full benchmark suite across all strategies and seeds."""
    if config_path is None:
        config_path = os.path.join(BASE_DIR, "configs", "config.yaml")
        
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            
    if seeds is None:
        seeds = config.get("simulation", {}).get("default_seeds", [42, 101, 2024, 777])
        
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, "experiments", "results")
    os.makedirs(output_dir, exist_ok=True)

    strategies = [
        ("fixed_time", "Fixed-Time (Baseline)"),
        ("negotiated_directional", "Negotiated Directional"),
        ("fairness_aware", "Fairness-Aware (Proposed)")
    ]

    all_results = []
    print(f"============================================================")
    print(f"Starting P25 Traffic Orchestration Benchmark across {len(seeds)} seeds...")
    print(f"Strategies: {[s[1] for s in strategies]}")
    print(f"============================================================")

    for strat_key, strat_label in strategies:
        print(f"\nEvaluating Strategy: {strat_label}")
        for seed in seeds:
            print(f"  -> Running seed {seed}...", end="", flush=True)
            summary, _ = run_single_simulation(strat_key, seed, config=config, total_steps=total_steps)
            summary["strategy_label"] = strat_label
            all_results.append(summary)
            print(f" Done! Avg Wait: {summary['avg_waiting_time_s']}s | Max Wait: {summary['max_waiting_time_s']}s | Completion: {summary['completion_rate_pct']}%")

    # Save to JSON
    json_path = os.path.join(output_dir, "benchmark_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    # Save flat CSV for tabular display
    df = pd.DataFrame(all_results)
    # Exclude complex nested dict for simple CSV
    cols = [
        "strategy_label", "strategy", "seed",
        "avg_waiting_time_s", "max_waiting_time_s", "p95_waiting_time_s",
        "completion_rate_pct", "total_departed", "total_arrived",
        "fairness_gini_index", "total_phase_switches", "simulation_duration_s"
    ]
    df_clean = df[[c for c in cols if c in df.columns]]
    csv_path = os.path.join(output_dir, "benchmark_summary.csv")
    df_clean.to_csv(csv_path, index=False)

    print(f"\n============================================================")
    print(f"Benchmark finished successfully! Results saved to:")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    print(f"============================================================")
    
    # Calculate aggregated summary comparison
    agg_df = df.groupby("strategy_label").agg({
        "avg_waiting_time_s": ["mean", "std"],
        "max_waiting_time_s": ["mean", "std"],
        "completion_rate_pct": ["mean", "std"],
        "fairness_gini_index": ["mean"]
    }).round(2)
    print("\nAggregate Statistical Comparison across seeds:")
    print(agg_df)
    
    return all_results, df_clean

if __name__ == "__main__":
    run_full_benchmark()
