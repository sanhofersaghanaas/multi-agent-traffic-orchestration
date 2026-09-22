"""
Fairness-Aware Multi-Modal Orchestration Agent (Strategy 3 - Proposed).
Integrates:
1. Directional queue pressure
2. Multi-modal priority weighting (passenger car, bus, emergency)
3. Non-linear fairness aging & starvation mitigation
4. Green-wave coordination bonuses with neighboring junction agents
"""

from agents.base_agent import BaseJunctionAgent

class FairnessAwareAgent(BaseJunctionAgent):
    def __init__(self, junction_id, config=None):
        super().__init__(junction_id, config)
        
        fairness_cfg = self.config.get("fairness_mechanism", {})
        self.aging_factor = fairness_cfg.get("aging_factor", 1.35)
        self.wait_weight = fairness_cfg.get("wait_weight", 0.45)
        self.pressure_weight = fairness_cfg.get("pressure_weight", 0.55)
        self.coordination_bonus = fairness_cfg.get("coordination_bonus", 3.5)
        self.starvation_threshold = fairness_cfg.get("starvation_threshold", 45)
        
        modal_cfg = self.config.get("traffic_demand", {}).get("modal_weights", {})
        self.car_weight = modal_cfg.get("car", 1.0)
        self.bus_weight = modal_cfg.get("bus", 2.5)
        self.emergency_weight = modal_cfg.get("emergency", 6.0)
        
        # Telemetry log for visualization
        self.last_bids = {"NS": 0.0, "EW": 0.0}
        self.bid_breakdown = {}

    def _compute_approach_score(self, approach_data):
        """Computes multi-modal pressure and wait penalty for a single approach."""
        q_len = approach_data.get("queue_length", 0)
        avg_wait = approach_data.get("avg_wait_time", 0.0)
        max_wait = approach_data.get("max_wait_time", 0.0)
        modal = approach_data.get("modal_counts", {})
        
        # Multi-modal weighted demand
        weighted_queue = (
            modal.get("car", 0) * self.car_weight +
            modal.get("bus", 0) * self.bus_weight +
            modal.get("emergency", 0) * self.emergency_weight
        )
        
        # Non-linear fairness aging penalty
        # Combines average wait and maximum wait to protect individual starved vehicles
        effective_wait = (avg_wait * 0.4) + (max_wait * 0.6)
        aging_penalty = ((effective_wait / 15.0) ** self.aging_factor) * 2.0
        
        # Severe starvation escalation: if any vehicle waits > starvation_threshold, escalate bid
        is_starved = max_wait >= self.starvation_threshold
        starvation_escalation = 15.0 if is_starved else 0.0
        
        # Emergency preemption: if emergency vehicle present, escalate immediately
        emergency_escalation = 30.0 if modal.get("emergency", 0) > 0 else 0.0

        total_score = (
            self.pressure_weight * weighted_queue +
            self.wait_weight * aging_penalty +
            starvation_escalation +
            emergency_escalation
        )
        
        return {
            "score": total_score,
            "weighted_queue": weighted_queue,
            "aging_penalty": aging_penalty,
            "is_starved": is_starved,
            "has_emergency": modal.get("emergency", 0) > 0,
            "max_wait": max_wait
        }

    def compute_priority_bids(self, junction_state, neighbor_messages=None):
        approaches = junction_state.get("approaches", {})
        
        n_res = self._compute_approach_score(approaches.get("N", {}))
        s_res = self._compute_approach_score(approaches.get("S", {}))
        e_res = self._compute_approach_score(approaches.get("E", {}))
        w_res = self._compute_approach_score(approaches.get("W", {}))
        
        bid_ns = n_res["score"] + s_res["score"]
        bid_ew = e_res["score"] + w_res["score"]
        
        # Inter-agent neighbor coordination bonus (green wave synchronization)
        coord_bonus_ns = 0.0
        coord_bonus_ew = 0.0
        if neighbor_messages:
            for neighbor_id, msg in neighbor_messages.items():
                n_phase = msg.get("current_phase", 0)
                n_bids = msg.get("bids", {})
                
                # If neighbor along N-S axis is green and has high flow, add green-wave coordination bonus
                if ("J0_" in self.junction_id and "J1_" in neighbor_id) or ("J1_" in self.junction_id and "J0_" in neighbor_id):
                    if n_phase == 0:
                        coord_bonus_ns += self.coordination_bonus * 0.5
                # If neighbor along E-W axis is green and has high flow
                elif ("_0" in self.junction_id and "_1" in neighbor_id) or ("_1" in self.junction_id and "_0" in neighbor_id):
                    if n_phase == 2:
                        coord_bonus_ew += self.coordination_bonus * 0.5
                        
        bid_ns += coord_bonus_ns
        bid_ew += coord_bonus_ew
        
        self.last_bids = {"NS": round(bid_ns, 2), "EW": round(bid_ew, 2)}
        self.bid_breakdown = {
            "NS": {
                "queue_score": n_res["weighted_queue"] + s_res["weighted_queue"],
                "aging_penalty": n_res["aging_penalty"] + s_res["aging_penalty"],
                "coord_bonus": coord_bonus_ns,
                "has_starvation": n_res["is_starved"] or s_res["is_starved"],
                "has_emergency": n_res["has_emergency"] or s_res["has_emergency"],
                "max_wait": max(n_res["max_wait"], s_res["max_wait"])
            },
            "EW": {
                "queue_score": e_res["weighted_queue"] + w_res["weighted_queue"],
                "aging_penalty": e_res["aging_penalty"] + w_res["aging_penalty"],
                "coord_bonus": coord_bonus_ew,
                "has_starvation": e_res["is_starved"] or w_res["is_starved"],
                "has_emergency": e_res["has_emergency"] or w_res["has_emergency"],
                "max_wait": max(e_res["max_wait"], w_res["max_wait"])
            }
        }
        return bid_ns, bid_ew

    def compute_desired_phase(self, junction_state, neighbor_messages=None, force_switch=False):
        bid_ns, bid_ew = self.compute_priority_bids(junction_state, neighbor_messages)
        
        if force_switch:
            return 2 if self.current_phase == 0 else 0
            
        # Decision logic with hysteresis
        margin = 1.0
        if self.current_phase == 0: # currently NS Green
            # Switch to EW if EW bid is higher, OR if EW has active emergency/starvation
            if bid_ew > (bid_ns + margin) or self.bid_breakdown["EW"]["has_starvation"] or self.bid_breakdown["EW"]["has_emergency"]:
                return 2
            return 0
        else: # currently EW Green
            if bid_ns > (bid_ew + margin) or self.bid_breakdown["NS"]["has_starvation"] or self.bid_breakdown["NS"]["has_emergency"]:
                return 0
            return 2

    def get_outgoing_bid(self, junction_state):
        return {
            "junction_id": self.junction_id,
            "current_phase": self.current_phase,
            "bids": self.last_bids,
            "breakdown": self.bid_breakdown
        }
