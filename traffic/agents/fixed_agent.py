"""
Fixed-Time Signal Control Agent (Strategy 1 - Baseline).
Operates on a pre-determined, rigid cycle split irrespective of real-time demand.
"""

from agents.base_agent import BaseJunctionAgent

class FixedTimeAgent(BaseJunctionAgent):
    def __init__(self, junction_id, config=None, cycle_split=30):
        super().__init__(junction_id, config)
        # Standard fixed green duration for each phase
        self.fixed_green_duration = cycle_split

    def compute_desired_phase(self, junction_state, neighbor_messages=None, force_switch=False):
        # Switch to opposite phase strictly after fixed green time has elapsed
        if self.time_in_current_phase >= self.fixed_green_duration or force_switch:
            return 2 if self.current_phase == 0 else 0
        return self.current_phase
