"""
Global Configuration for P25 - Dynamic Multi-Modal Traffic Orchestration Network
"""

import os

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SUMO_CONFIG_DIR = os.path.join(BASE_DIR, "sumo_files")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SUMO_CONFIG_DIR, exist_ok=True)

# Grid Network Setup (2x2 Junction Network)
GRID_ROWS = 2
GRID_COLS = 2

JUNCTION_IDS = [f"J_{r}_{c}" for r in range(GRID_ROWS) for c in range(GRID_COLS)]

# Directional Approaches per Junction
DIRECTIONS = ["N", "S", "E", "W"]

# Phase Definitions
# Phase 0: North-South Green (NS_GREEN)
# Phase 1: North-South Yellow (NS_YELLOW)
# Phase 2: East-West Green (EW_GREEN)
# Phase 3: East-West Yellow (EW_YELLOW)
PHASE_NS_GREEN = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN = 2
PHASE_EW_YELLOW = 3

MIN_GREEN_TIME = 10   # seconds
MAX_GREEN_TIME = 45   # seconds
YELLOW_TIME = 3       # seconds

# Vehicle Types and Priority Weights for Multi-Modal Pressure
VEHICLE_WEIGHTS = {
    "car": 1.0,
    "bus": 2.5,
    "emergency": 5.0,
    "pedestrian": 0.5
}

VEHICLE_PROBABILITIES = {
    "car": 0.75,
    "bus": 0.15,
    "emergency": 0.05,
    "pedestrian": 0.05
}

# Fairness & Starvation Thresholds
MAX_WAIT_TIME_THRESHOLD = 45.0  # seconds - triggers fairness priority boost
STARVATION_CYCLE_THRESHOLD = 3   # phase cycles skipped before forcing green

# Inter-Agent Bidding & Negotiation
NEIGHBOR_BID_WEIGHT = 0.35      # Influence weight of adjacent agent requests

# Benchmark Seeds
BENCHMARK_SEEDS = [42, 101, 2024]
DEFAULT_SIMULATION_STEPS = 300  # seconds per experiment run
