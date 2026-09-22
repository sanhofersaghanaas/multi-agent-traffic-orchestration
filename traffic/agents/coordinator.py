"""
Multi-Agent Coordinator & Inter-Junction Message Bus.
Manages neighbor communication topologies and orchestrates distributed control.
"""

from agents.fixed_agent import FixedTimeAgent
from agents.directional_agent import NegotiatedDirectionalAgent
from agents.fairness_agent import FairnessAwareAgent

class MultiAgentCoordinator:
    def __init__(self, strategy_type="fairness_aware", config=None):
        self.strategy_type = strategy_type
        self.config = config or {}
        
        # Grid Adjacency Graph for 2x2 network
        self.neighbors_map = {
            "J0_0": ["J0_1", "J1_0"],
            "J0_1": ["J0_0", "J1_1"],
            "J1_0": ["J1_1", "J0_0"],
            "J1_1": ["J1_0", "J0_1"]
        }
        
        self.agents = {}
        self.latest_messages = {}
        self._initialize_agents()

    def _initialize_agents(self):
        for j_id in ["J0_0", "J0_1", "J1_0", "J1_1"]:
            if self.strategy_type == "fixed_time":
                self.agents[j_id] = FixedTimeAgent(j_id, self.config)
            elif self.strategy_type == "negotiated_directional":
                self.agents[j_id] = NegotiatedDirectionalAgent(j_id, self.config)
            elif self.strategy_type == "fairness_aware":
                self.agents[j_id] = FairnessAwareAgent(j_id, self.config)
            else:
                raise ValueError(f"Unknown strategy: {self.strategy_type}")
                
            self.latest_messages[j_id] = {}

    def step(self, env):
        """Orchestrates one step across all agents and updates environment."""
        states = env.get_all_junction_states()
        new_messages = {}
        
        # Step each agent with neighbor messages
        for j_id, agent in self.agents.items():
            j_state = states[j_id]
            
            # Fetch messages only from topological neighbors
            neighbor_msgs = {
                n_id: self.latest_messages[n_id]
                for n_id in self.neighbors_map.get(j_id, [])
                if n_id in self.latest_messages
            }
            
            # Agent decision
            old_phase = agent.current_phase
            new_phase = agent.step(j_state, neighbor_msgs)
            is_switch = (new_phase != old_phase and new_phase in [0, 2])
            
            # Apply to environment
            env.set_junction_phase(j_id, new_phase)
            env.metrics.record_junction_action(j_id, new_phase, is_switch)
            
            # Outgoing bid/state publication for next step
            new_messages[j_id] = agent.get_outgoing_bid(j_state)
            
        self.latest_messages = new_messages
