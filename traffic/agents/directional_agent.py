"""
Negotiated Directional Control Agent (Strategy 2).
Uses Max-Pressure directional queue sensing and inter-junction spillback negotiation,
without fairness/aging mechanisms.
"""

from agents.base_agent import BaseJunctionAgent

class NegotiatedDirectionalAgent(BaseJunctionAgent):
    def __init__(self, junction_id, config=None):
        super().__init__(junction_id, config)
        self.last_decision = 0
        self.pressure_history = {"NS": 0.0, "EW": 0.0}

    def compute_directional_pressure(self, junction_state, neighbor_messages=None):
        approaches = junction_state.get("approaches", {})
        
        q_n = approaches.get("N", {}).get("queue_length", 0)
        q_s = approaches.get("S", {}).get("queue_length", 0)
        q_e = approaches.get("E", {}).get("queue_length", 0)
        q_w = approaches.get("W", {}).get("queue_length", 0)
        
        # Base directional queue pressure
        pressure_ns = float(q_n + q_s)
        pressure_ew = float(q_e + q_w)
        
        # Neighbor spillback penalty: if downstream neighbor has long queues, penalize flow in that direction
        if neighbor_messages:
            for neighbor_id, msg in neighbor_messages.items():
                downstream_q = msg.get("total_queue", 0)
                # If neighbor has high queue (>15 veh), apply spillback penalty
                if downstream_q > 15:
                    if "J0_" in self.junction_id and "J1_" in neighbor_id: # N/S neighbor
                        pressure_ns = max(0.0, pressure_ns - 0.2 * downstream_q)
                    elif "_0" in self.junction_id and "_1" in neighbor_id: # E/W neighbor
                        pressure_ew = max(0.0, pressure_ew - 0.2 * downstream_q)
                        
        self.pressure_history["NS"] = pressure_ns
        self.pressure_history["EW"] = pressure_ew
        return pressure_ns, pressure_ew

    def compute_desired_phase(self, junction_state, neighbor_messages=None, force_switch=False):
        pressure_ns, pressure_ew = self.compute_directional_pressure(junction_state, neighbor_messages)
        
        if force_switch:
            return 2 if self.current_phase == 0 else 0
            
        # Hysteresis margin to prevent rapid flickering
        margin = 1.5
        if self.current_phase == 0: # currently NS Green
            if pressure_ew > (pressure_ns + margin):
                return 2 # switch to EW Green
            return 0
        else: # currently EW Green
            if pressure_ns > (pressure_ew + margin):
                return 0 # switch to NS Green
            return 2

    def get_outgoing_bid(self, junction_state):
        approaches = junction_state.get("approaches", {})
        total_q = sum(a.get("queue_length", 0) for a in approaches.values())
        return {
            "junction_id": self.junction_id,
            "current_phase": self.current_phase,
            "total_queue": total_q,
            "pressures": self.pressure_history
        }
