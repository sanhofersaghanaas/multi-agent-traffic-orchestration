"""
Standalone High-Fidelity Python Traffic Simulator
Provides discrete-event simulation of vehicle queues, multi-modal arrivals,
downstream edge transfers, and signal phase control across a 2x2 grid network.
"""

import random
from config import GRID_ROWS, GRID_COLS, JUNCTION_IDS, PHASE_NS_GREEN, PHASE_EW_GREEN

class Vehicle:
    def __init__(self, veh_id, vtype, origin, destination, spawn_time):
        self.veh_id = veh_id
        self.vtype = vtype
        self.origin = origin
        self.destination = destination
        self.spawn_time = spawn_time
        self.wait_time = 0.0
        self.travel_time = 0.0
        self.current_junction = origin
        self.current_approach = "N" # 'N', 'S', 'E', 'W'
        self.in_queue = True
        self.is_completed = False

class PythonTrafficEnv:
    def __init__(self, seed=42, max_steps=300):
        self.seed = seed
        self.max_steps = max_steps
        self.rng = random.Random(seed)
        
        self.step_count = 0
        self.vehicles = {}  # veh_id -> Vehicle
        self.completed_vehicles = []
        
        # Structure: junction_id -> approach ('N','S','E','W') -> list of Vehicles
        self.queues = {
            j_id: {d: [] for d in ["N", "S", "E", "W"]}
            for j_id in JUNCTION_IDS
        }
        
        # Network signal phases: junction_id -> phase_code
        self.phase_states = {j_id: PHASE_NS_GREEN for j_id in JUNCTION_IDS}

    def reset(self):
        """Resets simulation environment state."""
        self.rng = random.Random(self.seed)
        self.step_count = 0
        self.vehicles.clear()
        self.completed_vehicles.clear()
        self.queues = {
            j_id: {d: [] for d in ["N", "S", "E", "W"]}
            for j_id in JUNCTION_IDS
        }
        self.phase_states = {j_id: PHASE_NS_GREEN for j_id in JUNCTION_IDS}
        return self._get_network_observation()

    def _spawn_vehicles(self):
        """Random multi-modal vehicle spawning based on seed probability."""
        if self.step_count > self.max_steps - 30:
            return # Stop spawning near end of sim

        # Demand density factor
        spawn_chance = 0.40 + 0.20 * math_sin(self.step_count / 30.0)

        if self.rng.random() < spawn_chance:
            vtype_roll = self.rng.random()
            if vtype_roll < 0.70:
                vtype = "car"
            elif vtype_roll < 0.85:
                vtype = "bus"
            elif vtype_roll < 0.93:
                vtype = "emergency"
            else:
                vtype = "pedestrian"

            j_id = self.rng.choice(JUNCTION_IDS)
            approach = self.rng.choice(["N", "S", "E", "W"])

            veh_id = f"v_{self.step_count}_{len(self.vehicles)}"
            veh = Vehicle(veh_id, vtype, j_id, None, self.step_count)
            veh.current_junction = j_id
            veh.current_approach = approach

            self.vehicles[veh_id] = veh
            self.queues[j_id][approach].append(veh)

    def step(self, phase_actions):
        """
        Advances simulation by 1 second.
        phase_actions: dict mapping junction_id -> active phase code (0, 1, 2, or 3)
        """
        self.step_count += 1
        self.phase_states = phase_actions

        # 1. Spawn new vehicle arrivals
        self._spawn_vehicles()

        # 2. Update waiting times and discharge green approaches
        for j_id in JUNCTION_IDS:
            active_phase = self.phase_states.get(j_id, PHASE_NS_GREEN)

            # Determine allowed green directions
            green_directions = []
            if active_phase == PHASE_NS_GREEN:
                green_directions = ["N", "S"]
            elif active_phase == PHASE_EW_GREEN:
                green_directions = ["E", "W"]
            # Yellow phases (1 & 3) allow reduced/cautious discharge

            for approach in ["N", "S", "E", "W"]:
                q = self.queues[j_id][approach]

                if approach in green_directions and len(q) > 0:
                    # Discharge 1-2 vehicles per green step
                    discharge_count = min(len(q), 2 if q[0].vtype == "emergency" else 1)
                    for _ in range(discharge_count):
                        passed_veh = q.pop(0)
                        passed_veh.travel_time = self.step_count - passed_veh.spawn_time
                        
                        # 60% probability of exiting grid, 40% probability of routing to adjacent junction
                        if self.rng.random() < 0.60:
                            passed_veh.is_completed = True
                            self.completed_vehicles.append(passed_veh)
                        else:
                            # Transfer to neighbor
                            neighbor_j = self._get_downstream_junction(j_id, approach)
                            if neighbor_j and neighbor_j in self.queues:
                                new_app = self._opposite_direction(approach)
                                passed_veh.current_junction = neighbor_j
                                passed_veh.current_approach = new_app
                                self.queues[neighbor_j][new_app].append(passed_veh)
                            else:
                                passed_veh.is_completed = True
                                self.completed_vehicles.append(passed_veh)

                # Accumulate waiting time for stopped vehicles in queue
                for veh in q:
                    veh.wait_time += 1.0

        return self._get_network_observation()

    def _get_downstream_junction(self, j_id, approach):
        """Returns neighbor junction ID downstream of approach."""
        r, c = map(int, j_id.split("_")[1:])
        if approach == "N" and r > 0: return f"J_{r-1}_{c}"
        if approach == "S" and r < GRID_ROWS - 1: return f"J_{r+1}_{c}"
        if approach == "W" and c > 0: return f"J_{r}_{c-1}"
        if approach == "E" and c < GRID_COLS - 1: return f"J_{r}_{c+1}"
        return None

    def _opposite_direction(self, approach):
        opp = {"N": "S", "S": "N", "E": "W", "W": "E"}
        return opp.get(approach, "N")

    def _get_network_observation(self):
        """
        Returns structured telemetry dictionary for agent perception and dashboard visualizations.
        """
        obs = {}
        for j_id in JUNCTION_IDS:
            queues_breakdown = {}
            wait_times = {}
            downstream = {}

            for d in ["N", "S", "E", "W"]:
                q_list = self.queues[j_id][d]
                
                # Breakdown by vehicle type
                q_counts = {"car": 0, "bus": 0, "emergency": 0, "pedestrian": 0}
                max_w = 0.0
                tot_w = 0.0

                for veh in q_list:
                    q_counts[veh.vtype] = q_counts.get(veh.vtype, 0) + 1
                    if veh.wait_time > max_w:
                        max_w = veh.wait_time
                    tot_w += veh.wait_time

                queues_breakdown[d] = q_counts
                wait_times[d] = {"max": max_w, "total": tot_w, "avg": tot_w / max(1, len(q_list))}
                
                downstream_j = self._get_downstream_junction(j_id, d)
                if downstream_j:
                    opp_d = self._opposite_direction(d)
                    downstream[d] = len(self.queues[downstream_j][opp_d])
                else:
                    downstream[d] = 0

            obs[j_id] = {
                "queues": queues_breakdown,
                "wait_times": wait_times,
                "downstream": downstream
            }
        return obs

    def get_summary_metrics(self):
        """Returns overall performance metrics for evaluation."""
        all_active = [veh for q_j in self.queues.values() for q_d in q_j.values() for veh in q_d]
        total_spawned = len(self.vehicles)
        total_completed = len(self.completed_vehicles)

        completion_rate = (total_completed / max(1, total_spawned)) * 100.0

        wait_times = [v.wait_time for v in all_active] + [v.wait_time for v in self.completed_vehicles]
        avg_wait_time = sum(wait_times) / max(1, len(wait_times))
        max_wait_time = max(wait_times) if wait_times else 0.0
        total_delay = sum(wait_times)

        return {
            "total_spawned": total_spawned,
            "total_completed": total_completed,
            "completion_rate": round(completion_rate, 2),
            "avg_wait_time": round(avg_wait_time, 2),
            "max_wait_time": round(max_wait_time, 2),
            "total_delay": round(total_delay, 2),
            "simulation_steps": self.step_count
        }

def math_sin(val):
    import math
    return math.sin(val)
