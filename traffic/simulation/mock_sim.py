"""
High-Fidelity Discrete-Event Simulation Engine for P25 Traffic Orchestration Network.
Provides an identical API to TraCI for 2x2 interconnected traffic light junctions.
Guarantees reliable local execution, demonstration, and benchmarking.
"""

import random
from collections import deque

class MockTraCI:
    def __init__(self, seed=42, total_steps=360):
        self.seed = seed
        self.total_steps = total_steps
        self.rng = random.Random(seed)
        self.current_step = 0
        
        # 4 Junctions in a 2x2 grid
        self.junctions = ["J0_0", "J0_1", "J1_0", "J1_1"]
        
        # Approaches per junction: 'N' (from North heading South), 'S', 'E', 'W'
        # Directional mapping to phase:
        # Phase 0: NS Green ("GGggrrrrGGggrrrr")
        # Phase 1: NS Yellow ("yyyyrrrryyyyrrrr")
        # Phase 2: EW Green ("rrrrGGggrrrrGGgg")
        # Phase 3: EW Yellow ("rrrryyyyrrrryyyy")
        self.traffic_lights = {}
        for j_id in self.junctions:
            self.traffic_lights[j_id] = {
                "state": "GGggrrrrGGggrrrr",
                "phase_index": 0,
                "time_in_phase": 0
            }
            
        # Lane queues: (junction_id, direction) -> deque of vehicle dicts
        # Directions: 'N', 'S', 'E', 'W'
        self.lane_queues = {}
        for j_id in self.junctions:
            for d in ['N', 'S', 'E', 'W']:
                self.lane_queues[(j_id, d)] = deque()
                
        # Inter-junction links with transit delays: (upstream_j, dir) -> (downstream_j, downstream_dir, travel_time)
        self.topology = {
            ("J0_0", "W"): ("J0_1", "W", 8), # flowing East: from J0_0 exits toward J0_1 entering its West approach
            ("J0_1", "E"): ("J0_0", "E", 8), # flowing West: from J0_1 exits toward J0_0 entering its East approach
            ("J1_0", "W"): ("J1_1", "W", 8),
            ("J1_1", "E"): ("J1_0", "E", 8),
            ("J0_0", "S"): ("J1_0", "S", 8), # flowing North: from J0_0 exits toward J1_0 entering its South approach
            ("J1_0", "N"): ("J0_0", "N", 8), # flowing South: from J1_0 exits toward J0_0 entering its North approach
            ("J0_1", "S"): ("J1_1", "S", 8),
            ("J1_1", "N"): ("J0_1", "N", 8),
        }
        
        # Vehicles in transit between junctions: list of dicts {veh, dest_junction, dest_direction, arrival_step}
        self.in_transit = []
        
        # Vehicle records
        self.active_vehicles = {}
        self.departed_count = 0
        self.arrived_count = 0
        self.veh_counter = 0

    def get_phase_state_string(self, phase_index):
        if phase_index == 0:
            return "GGggrrrrGGggrrrr" # NS Green
        elif phase_index == 1:
            return "yyyyrrrryyyyrrrr" # NS Yellow
        elif phase_index == 2:
            return "rrrrGGggrrrrGGgg" # EW Green
        elif phase_index == 3:
            return "rrrryyyyrrrryyyy" # EW Yellow
        return "GGggrrrrGGggrrrr"

    def set_tls_state(self, tls_id, state_str_or_index):
        if isinstance(state_str_or_index, int):
            self.traffic_lights[tls_id]["phase_index"] = state_str_or_index
            self.traffic_lights[tls_id]["state"] = self.get_phase_state_string(state_str_or_index)
        else:
            self.traffic_lights[tls_id]["state"] = state_str_or_index
            if "GGggrrrr" in state_str_or_index:
                self.traffic_lights[tls_id]["phase_index"] = 0
            elif "yyyyrrrr" in state_str_or_index:
                self.traffic_lights[tls_id]["phase_index"] = 1
            elif "rrrrGGgg" in state_str_or_index:
                self.traffic_lights[tls_id]["phase_index"] = 2
            elif "rrrryyyy" in state_str_or_index:
                self.traffic_lights[tls_id]["phase_index"] = 3

    def get_tls_state(self, tls_id):
        return self.traffic_lights[tls_id]["state"]

    def _spawn_boundary_vehicles(self):
        # Inflows arriving from perimeter boundaries into outer approaches
        boundary_entries = [
            ("J0_0", "W"), ("J1_0", "W"), # West entry
            ("J0_1", "E"), ("J1_1", "E"), # East entry
            ("J0_0", "S"), ("J0_1", "S"), # South entry
            ("J1_0", "N"), ("J1_1", "N")  # North entry
        ]
        
        for j_id, direction in boundary_entries:
            # Multi-modal departure probability
            p = self.rng.random()
            if p < 0.22: # Passenger Car
                v_type = "car"
            elif p < 0.26: # Bus
                v_type = "bus"
            elif p < 0.275: # Emergency
                v_type = "emergency"
            else:
                continue
                
            self.veh_counter += 1
            veh_id = f"{v_type}_{self.veh_counter}"
            veh = {
                "id": veh_id,
                "type": v_type,
                "depart_step": self.current_step,
                "waiting_time": 0.0,
                "is_stopped": True,
                "speed": 0.0,
                "current_j": j_id,
                "current_dir": direction,
                "distance_to_stop": 15.0 + len(self.lane_queues[(j_id, direction)]) * 6.0
            }
            self.lane_queues[(j_id, direction)].append(veh)
            self.active_vehicles[veh_id] = veh
            self.departed_count += 1

    def simulationStep(self):
        self.current_step += 1
        
        # 1. Spawn new vehicles at perimeter
        self._spawn_boundary_vehicles()
        
        # 2. Process in-transit vehicles arriving at downstream junctions
        still_in_transit = []
        for trip in self.in_transit:
            if trip["arrival_step"] <= self.current_step:
                dest_j = trip["dest_junction"]
                dest_d = trip["dest_direction"]
                veh = trip["veh"]
                veh["current_j"] = dest_j
                veh["current_dir"] = dest_d
                veh["is_stopped"] = True
                veh["speed"] = 0.0
                self.lane_queues[(dest_j, dest_d)].append(veh)
            else:
                still_in_transit.append(trip)
        self.in_transit = still_in_transit
        
        # 3. Serve vehicles at each junction based on traffic light phase
        for j_id in self.junctions:
            tls = self.traffic_lights[j_id]
            phase = tls["phase_index"]
            tls["time_in_phase"] += 1
            
            # Phase 0: NS Green -> 'N' and 'S' can discharge
            # Phase 2: EW Green -> 'E' and 'W' can discharge
            active_dirs = []
            if phase == 0:
                active_dirs = ['N', 'S']
            elif phase == 2:
                active_dirs = ['E', 'W']
                
            for d in ['N', 'S', 'E', 'W']:
                q = self.lane_queues[(j_id, d)]
                if d in active_dirs and len(q) > 0:
                    # Discharge up to 2 vehicles per second (2 lanes saturation flow)
                    discharge_count = min(2, len(q))
                    for _ in range(discharge_count):
                        veh = q.popleft()
                        veh["is_stopped"] = False
                        veh["speed"] = 13.89
                        
                        # Check if vehicle transfers to downstream junction or exits network
                        link_key = (j_id, d)
                        if link_key in self.topology:
                            down_j, down_d, t_time = self.topology[link_key]
                            self.in_transit.append({
                                "veh": veh,
                                "dest_junction": down_j,
                                "dest_direction": down_d,
                                "arrival_step": self.current_step + t_time
                            })
                        else:
                            # Arrived / completed trip outside grid
                            self.arrived_count += 1
                            if veh["id"] in self.active_vehicles:
                                del self.active_vehicles[veh["id"]]
                                
                # Remaining vehicles in queue wait and accumulate waiting time
                for veh in q:
                    veh["is_stopped"] = True
                    veh["waiting_time"] += 1.0
                    veh["speed"] = 0.0

    # Query APIs mirroring TraCI
    def get_halting_count(self, junction_id, direction):
        return len(self.lane_queues.get((junction_id, direction), []))

    def get_lane_waiting_time(self, junction_id, direction):
        q = self.lane_queues.get((junction_id, direction), [])
        if not q:
            return 0.0
        return sum(v["waiting_time"] for v in q) / len(q)

    def get_lane_max_wait(self, junction_id, direction):
        q = self.lane_queues.get((junction_id, direction), [])
        if not q:
            return 0.0
        return max(v["waiting_time"] for v in q)

    def get_lane_modal_counts(self, junction_id, direction):
        q = self.lane_queues.get((junction_id, direction), [])
        counts = {"car": 0, "bus": 0, "emergency": 0}
        for v in q:
            t = v.get("type", "car")
            counts[t] = counts.get(t, 0) + 1
        return counts

    def get_total_queue(self):
        return sum(len(q) for q in self.lane_queues.values())

    def get_active_waiting_times(self):
        return [v["waiting_time"] for v in self.active_vehicles.values()]

    def close(self):
        pass
