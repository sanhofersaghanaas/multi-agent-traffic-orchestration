"""
Multi-Agent Network Orchestrator
Manages the graph topology of junction agents, inter-agent communication protocol,
neighbor bidding exchanges, and network-wide telemetry logging.
"""

from agents.traffic_agent import TrafficAgent
from config import GRID_ROWS, GRID_COLS, JUNCTION_IDS

class MultiAgentNetwork:
    def __init__(self):
        self.agents = {}
        self.communication_logs = []
        self._initialize_grid_topology()

    def _initialize_grid_topology(self):
        """Initializes 2x2 grid junction agents and links neighbor topology."""
        # Create agents
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                j_id = f"J_{r}_{c}"
                self.agents[j_id] = TrafficAgent(j_id, r, c)

        # Connect neighbors
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                j_id = f"J_{r}_{c}"
                neighbors = {}
                if r > 0:
                    neighbors["N"] = f"J_{r-1}_{c}"
                if r < GRID_ROWS - 1:
                    neighbors["S"] = f"J_{r+1}_{c}"
                if c > 0:
                    neighbors["W"] = f"J_{r}_{c-1}"
                if c < GRID_COLS - 1:
                    neighbors["E"] = f"J_{r}_{c+1}"

                self.agents[j_id].set_neighbors(neighbors)

    def reset(self):
        """Resets network state and logs."""
        self.communication_logs.clear()
        self._initialize_grid_topology()

    def update_agent_perceptions(self, network_state):
        """
        Pushes latest sensor observation data from simulation engine to each agent.
        network_state: dict mapping junction_id -> {'queues': dict, 'wait_times': dict, 'downstream': dict}
        """
        for j_id, agent in self.agents.items():
            if j_id in network_state:
                state = network_state[j_id]
                agent.update_perception(
                    queues=state.get("queues", {}),
                    wait_times=state.get("wait_times", {}),
                    downstream_queues=state.get("downstream", {})
                )

    def orchestrate_inter_agent_communication(self, current_step):
        """
        Executes inter-agent priority bidding protocol:
        1. Each agent generates priority bid payload.
        2. Network broadcasts bids to direct spatial neighbors.
        3. Logs inter-agent messages for real-time visual inspection.
        """
        # Step 1: Collect bids
        bids = {j_id: agent.generate_bid() for j_id, agent in self.agents.items()}

        # Step 2: Distribute to neighbors and log interactions
        for j_id, agent in self.agents.items():
            neighbor_bids = {}
            for direction, neighbor_id in agent.neighbors.items():
                if neighbor_id in bids:
                    neighbor_bids[neighbor_id] = bids[neighbor_id]

                    # Log communication entry periodically
                    if current_step % 5 == 0:
                        self.communication_logs.append({
                            "step": current_step,
                            "sender": j_id,
                            "receiver": neighbor_id,
                            "direction": direction,
                            "preferred_dir": bids[j_id]["preferred_dir"],
                            "urgency": round(bids[j_id]["urgency"], 2),
                            "has_emergency": bids[j_id]["has_emergency"]
                        })

            agent.receive_neighbor_bids(neighbor_bids)

        # Keep communication logs bounded (last 200 entries)
        if len(self.communication_logs) > 200:
            self.communication_logs = self.communication_logs[-200:]

    def step_agents(self, strategy_type, current_step):
        """
        Executes step for all agents using specified strategy.
        Returns dict of chosen phase actions per junction.
        """
        # Run bidding protocol for agentic strategies
        if strategy_type == "fairness_aware":
            self.orchestrate_inter_agent_communication(current_step)

        actions = {}
        for j_id, agent in self.agents.items():
            actions[j_id] = agent.step(strategy_type)

        return actions
