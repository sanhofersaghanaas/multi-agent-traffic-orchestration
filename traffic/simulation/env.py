"""
Environment wrapper for P25 Multi-Modal Traffic Orchestration Network.
Provides a unified interface bridging TraCI (native SUMO) and MockTraCI (discrete-event simulation).
"""

import os
import sys
from simulation.mock_sim import MockTraCI
from simulation.metrics_tracker import MetricsTracker

class TrafficEnvironment:
    def __init__(self, config=None, seed=42, force_mock=False):
        self.config = config or {}
        self.seed = seed
        self.force_mock = force_mock
        self.use_traci = False
        self.step_count = 0
        self.total_steps = self.config.get("simulation", {}).get("total_steps", 360)
        
        self.junction_ids = ["J0_0", "J0_1", "J1_0", "J1_1"]
        self.directions = ["N", "S", "E", "W"]
        
        # Check SUMO availability unless force_mock is requested
        if not self.force_mock:
            self.use_traci = self._check_sumo_available()
            
        self.sim = None
        self.metrics = None
        self.reset(seed=self.seed)

    def _check_sumo_available(self):
        try:
            import traci
            sumo_home = os.environ.get("SUMO_HOME")
            if sumo_home and os.path.exists(sumo_home):
                return True
        except ImportError:
            pass
        return False

    def reset(self, seed=None):
        if seed is not None:
            self.seed = seed
            
        self.step_count = 0
        self.metrics = MetricsTracker(seed=self.seed)
        
        if self.use_traci:
            try:
                import traci
                # Close any lingering session
                try:
                    traci.close()
                except Exception:
                    pass
                sumo_binary = "sumo"
                cfg_path = os.path.join(os.path.dirname(__file__), "..", "sumo_files", "network.sumocfg")
                traci.start([sumo_binary, "-c", cfg_path, "--seed", str(self.seed), "--no-warnings", "true"])
                self.sim = traci
            except Exception as e:
                print(f"[TrafficEnvironment] Fallback to MockTraCI engine: {e}")
                self.use_traci = False
                self.sim = MockTraCI(seed=self.seed, total_steps=self.total_steps)
        else:
            self.sim = MockTraCI(seed=self.seed, total_steps=self.total_steps)

        return self.get_all_junction_states()

    def get_junction_state(self, junction_id):
        """Returns directional queues, average waiting times, max wait times, and modal counts."""
        state = {
            "junction_id": junction_id,
            "current_phase": self.sim.traffic_lights[junction_id]["phase_index"] if hasattr(self.sim, "traffic_lights") else 0,
            "time_in_phase": self.sim.traffic_lights[junction_id]["time_in_phase"] if hasattr(self.sim, "traffic_lights") else 0,
            "approaches": {}
        }
        
        for d in self.directions:
            if hasattr(self.sim, "get_halting_count"):
                q_len = self.sim.get_halting_count(junction_id, d)
                avg_w = self.sim.get_lane_waiting_time(junction_id, d)
                max_w = self.sim.get_lane_max_wait(junction_id, d)
                modal = self.sim.get_lane_modal_counts(junction_id, d)
            else:
                q_len = 0
                avg_w = 0.0
                max_w = 0.0
                modal = {"car": 0, "bus": 0, "emergency": 0}
                
            state["approaches"][d] = {
                "queue_length": q_len,
                "avg_wait_time": avg_w,
                "max_wait_time": max_w,
                "modal_counts": modal
            }
        return state

    def get_all_junction_states(self):
        return {j_id: self.get_junction_state(j_id) for j_id in self.junction_ids}

    def set_junction_phase(self, junction_id, phase_index):
        if hasattr(self.sim, "set_tls_state"):
            self.sim.set_tls_state(junction_id, phase_index)
        elif hasattr(self.sim, "trafficlight"):
            self.sim.trafficlight.setPhase(junction_id, phase_index)

    def step(self):
        self.step_count += 1
        
        # Advance simulation by one step
        self.sim.simulationStep()
        
        # Extract global telemetry for MetricsTracker
        if hasattr(self.sim, "get_active_waiting_times"):
            active_waits = self.sim.get_active_waiting_times()
            total_queue = self.sim.get_total_queue()
            active_count = len(self.sim.active_vehicles)
            arrived_count = self.sim.arrived_count
            departed_count = self.sim.departed_count
            
            # Sync tracker
            self.metrics.total_departed = departed_count
            self.metrics.total_arrived = arrived_count
            
            # Update individual vehicle records for comprehensive evaluation
            for v_id, v_data in self.sim.active_vehicles.items():
                if v_id not in self.metrics.vehicle_records:
                    self.metrics.register_departure(v_id, v_data.get("type", "car"), v_data.get("depart_step", self.step_count))
                self.metrics.update_vehicle_wait(v_id, 1.0 if v_data.get("is_stopped", True) else 0.0, is_stopped=v_data.get("is_stopped", True))
                
            self.metrics.record_step_metrics(self.step_count, active_waits, total_queue, active_count, arrived_count)
            
        done = self.step_count >= self.total_steps
        return self.get_all_junction_states(), done, self.metrics

    def close(self):
        if self.sim:
            self.sim.close()
