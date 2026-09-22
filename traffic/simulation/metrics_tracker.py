"""
Metrics Tracker for P25 Multi-Modal Traffic Orchestration Network.
Collects and aggregates performance metrics:
- Waiting Time (Average & Maximum per vehicle)
- Completion Rate (Departed vs Arrived)
- Simulation Duration & Delay
- Queue Lengths per Approach
- Multi-modal Performance Breakdown (Cars, Buses, Emergency)
- Fairness Metrics (Starvation Index & Waiting Time Dispersion)
"""

import numpy as np

class MetricsTracker:
    def __init__(self, strategy_name="unnamed", seed=42):
        self.strategy_name = strategy_name
        self.seed = seed
        
        self.step_history = []
        self.avg_wait_history = []
        self.max_wait_history = []
        self.queue_history = []
        self.active_vehicles_history = []
        self.arrived_vehicles_history = []
        
        # Vehicle lifetime records: veh_id -> {type, depart_time, arrival_time, total_wait, max_wait}
        self.vehicle_records = {}
        
        # Junction specific phase metrics
        self.junction_phase_switches = {}
        self.junction_green_allocations = {}
        
        self.total_departed = 0
        self.total_arrived = 0
        self.total_simulation_time = 0

    def register_departure(self, veh_id, veh_type, current_step):
        self.total_departed += 1
        if veh_id not in self.vehicle_records:
            self.vehicle_records[veh_id] = {
                "type": veh_type,
                "depart_time": current_step,
                "arrival_time": None,
                "total_wait": 0.0,
                "max_consecutive_wait": 0.0,
                "current_wait": 0.0
            }

    def update_vehicle_wait(self, veh_id, wait_increment, is_stopped=True):
        if veh_id in self.vehicle_records:
            rec = self.vehicle_records[veh_id]
            if is_stopped:
                rec["total_wait"] += wait_increment
                rec["current_wait"] += wait_increment
                if rec["current_wait"] > rec["max_consecutive_wait"]:
                    rec["max_consecutive_wait"] = rec["current_wait"]
            else:
                rec["current_wait"] = 0.0

    def register_arrival(self, veh_id, current_step):
        self.total_arrived += 1
        if veh_id in self.vehicle_records:
            self.vehicle_records[veh_id]["arrival_time"] = current_step
            self.vehicle_records[veh_id]["trip_duration"] = current_step - self.vehicle_records[veh_id]["depart_time"]

    def record_step_metrics(self, step, active_wait_times, total_queue, active_count, arrived_count):
        self.step_history.append(step)
        self.total_simulation_time = step
        
        if active_wait_times and len(active_wait_times) > 0:
            avg_w = float(np.mean(active_wait_times))
            max_w = float(np.max(active_wait_times))
        else:
            avg_w = 0.0
            max_w = 0.0
            
        self.avg_wait_history.append(avg_w)
        self.max_wait_history.append(max_w)
        self.queue_history.append(total_queue)
        self.active_vehicles_history.append(active_count)
        self.arrived_vehicles_history.append(arrived_count)

    def record_junction_action(self, junction_id, phase_id, is_switch=False):
        if junction_id not in self.junction_green_allocations:
            self.junction_green_allocations[junction_id] = {}
            self.junction_phase_switches[junction_id] = 0
            
        self.junction_green_allocations[junction_id][phase_id] = (
            self.junction_green_allocations[junction_id].get(phase_id, 0) + 1
        )
        if is_switch:
            self.junction_phase_switches[junction_id] += 1

    def get_summary(self):
        """Returns final aggregated metrics dictionary for evaluation."""
        waits = [r["total_wait"] for r in self.vehicle_records.values()]
        max_waits = [r["max_consecutive_wait"] for r in self.vehicle_records.values()]
        
        avg_wait = float(np.mean(waits)) if waits else 0.0
        p95_wait = float(np.percentile(waits, 95)) if waits else 0.0
        max_wait = float(np.max(max_waits)) if max_waits else 0.0
        std_wait = float(np.std(waits)) if waits else 0.0
        
        completion_rate = (self.total_arrived / self.total_departed * 100.0) if self.total_departed > 0 else 0.0
        
        # Breakdown by vehicle type
        modal_stats = {}
        for m in ["car", "bus", "emergency"]:
            m_waits = [r["total_wait"] for r in self.vehicle_records.values() if r["type"] == m]
            m_trips = [r.get("trip_duration", 0) for r in self.vehicle_records.values() if r["type"] == m and r["arrival_time"] is not None]
            modal_stats[m] = {
                "count": len(m_waits),
                "avg_wait": float(np.mean(m_waits)) if m_waits else 0.0,
                "avg_trip_time": float(np.mean(m_trips)) if m_trips else 0.0
            }

        # Fairness metric (Gini coefficient of waiting times)
        gini_index = 0.0
        if waits and len(waits) > 1 and np.sum(waits) > 0:
            sorted_waits = np.sort(waits)
            n = len(waits)
            index = np.arange(1, n + 1)
            gini_index = float((np.sum((2 * index - n - 1) * sorted_waits)) / (n * np.sum(sorted_waits)))

        return {
            "strategy": self.strategy_name,
            "seed": self.seed,
            "total_departed": self.total_departed,
            "total_arrived": self.total_arrived,
            "completion_rate_pct": round(completion_rate, 2),
            "avg_waiting_time_s": round(avg_wait, 2),
            "p95_waiting_time_s": round(p95_wait, 2),
            "max_waiting_time_s": round(max_wait, 2),
            "std_waiting_time_s": round(std_wait, 2),
            "fairness_gini_index": round(gini_index, 3),
            "simulation_duration_s": self.total_simulation_time,
            "total_phase_switches": sum(self.junction_phase_switches.values()),
            "modal_stats": modal_stats
        }
