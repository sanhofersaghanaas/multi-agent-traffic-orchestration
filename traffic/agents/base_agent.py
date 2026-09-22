"""
Abstract Base Traffic Light Agent for P25 Multi-Modal Traffic Orchestration Network.
Manages phase transitions, safety clearance intervals (yellow time), and green limits.
"""

from abc import ABC, abstractmethod

class BaseJunctionAgent(ABC):
    def __init__(self, junction_id, config=None):
        self.junction_id = junction_id
        self.config = config or {}
        
        sim_cfg = self.config.get("simulation", {})
        self.yellow_time = sim_cfg.get("yellow_time", 4)
        self.min_green_time = sim_cfg.get("min_green_time", 10)
        self.max_green_time = sim_cfg.get("max_green_time", 50)
        
        # State:
        # Phase 0: NS Green
        # Phase 1: NS Yellow (transitioning from 0 to 2)
        # Phase 2: EW Green
        # Phase 3: EW Yellow (transitioning from 2 to 0)
        self.current_phase = 0
        self.time_in_current_phase = 0
        self.target_phase = 0
        self.is_in_yellow_transition = False
        self.yellow_timer = 0

    def step(self, junction_state, neighbor_messages=None):
        """Advances agent state by one simulation step.
        Returns the active traffic light phase index (0, 1, 2, or 3)."""
        self.time_in_current_phase += 1
        
        # If currently serving a yellow clearance interval, decrement and transition
        if self.is_in_yellow_transition:
            self.yellow_timer -= 1
            if self.yellow_timer <= 0:
                self.is_in_yellow_transition = False
                self.current_phase = self.target_phase
                self.time_in_current_phase = 0
            return self.current_phase
            
        # If minimum green is not satisfied, stay in current phase
        if self.time_in_current_phase < self.min_green_time:
            return self.current_phase
            
        # If max green is exceeded, force consideration of switch
        force_switch = (self.time_in_current_phase >= self.max_green_time)
        
        # Decide desired green phase (0 for NS, 2 for EW)
        desired_green_phase = self.compute_desired_phase(junction_state, neighbor_messages, force_switch)
        
        # If desired phase differs from current active green phase, initiate yellow clearance
        if desired_green_phase != self.current_phase:
            self.target_phase = desired_green_phase
            self.is_in_yellow_transition = True
            self.yellow_timer = self.yellow_time
            # Phase 1 is yellow for NS->EW; Phase 3 is yellow for EW->NS
            self.current_phase = 1 if self.current_phase == 0 else 3
            self.time_in_current_phase = 0
            
        return self.current_phase

    @abstractmethod
    def compute_desired_phase(self, junction_state, neighbor_messages, force_switch=False):
        """Must return target green phase: 0 (NS Green) or 2 (EW Green)."""
        pass

    def get_outgoing_bid(self, junction_state):
        """Generates priority bid and status message to share with neighboring junctions."""
        return {
            "junction_id": self.junction_id,
            "current_phase": self.current_phase,
            "time_in_phase": self.time_in_current_phase
        }
