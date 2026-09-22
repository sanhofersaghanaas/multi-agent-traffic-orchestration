"""
Autonomous Traffic Light Junction AI Agent
Calculates directional pressure, tracks waiting time & multi-modal queues,
generates priority bids, communicates with neighbors, and enforces fairness constraints.
"""

from config import (
    PHASE_NS_GREEN, PHASE_NS_YELLOW, PHASE_EW_GREEN, PHASE_EW_YELLOW,
    MIN_GREEN_TIME, MAX_GREEN_TIME, YELLOW_TIME,
    VEHICLE_WEIGHTS, MAX_WAIT_TIME_THRESHOLD, STARVATION_CYCLE_THRESHOLD,
    NEIGHBOR_BID_WEIGHT
)

class TrafficAgent:
    def __init__(self, junction_id, row, col):
        self.junction_id = junction_id
        self.row = row
        self.col = col

        # Neighbors dictionary: {'N': id, 'S': id, 'E': id, 'W': id}
        self.neighbors = {}

        # Signal State
        self.current_phase = PHASE_NS_GREEN
        self.phase_duration = 0
        self.yellow_timer = 0
        self.pending_phase = None

        # Approach State (Queue counts per direction: 'N', 'S', 'E', 'W')
        # Structure per direction: {'car': int, 'bus': int, 'emergency': int, 'pedestrian': int}
        self.queues = {d: {"car": 0, "bus": 0, "emergency": 0, "pedestrian": 0} for d in ["N", "S", "E", "W"]}
        
        # Max and Avg waiting time per approach (seconds)
        self.max_wait_time = {"N": 0.0, "S": 0.0, "E": 0.0, "W": 0.0}
        self.total_wait_time = {"N": 0.0, "S": 0.0, "E": 0.0, "W": 0.0}
        
        # Outflow capacity/queue downstream
        self.downstream_queues = {"N": 0, "S": 0, "E": 0, "W": 0}

        # Starvation tracking
        self.cycles_since_green = {"NS": 0, "EW": 0}
        
        # Neighbor Bids received: {neighbor_id: bid_dict}
        self.received_bids = {}
        self.last_bid_sent = {}

    def set_neighbors(self, neighbors_dict):
        """Set adjacent junction agent IDs."""
        self.neighbors = neighbors_dict

    def update_perception(self, queues, wait_times, downstream_queues):
        """
        Updates sensor perception of incoming queues, vehicle waiting times, and downstream capacity.
        """
        self.queues = queues
        self.max_wait_time = {d: wait_times.get(d, {}).get("max", 0.0) for d in ["N", "S", "E", "W"]}
        self.total_wait_time = {d: wait_times.get(d, {}).get("total", 0.0) for d in ["N", "S", "E", "W"]}
        self.downstream_queues = downstream_queues

    def calculate_weighted_queue(self, direction):
        """Calculates multi-modal weighted queue length for a given approach direction."""
        q_dict = self.queues.get(direction, {})
        weighted_sum = sum(q_dict.get(vtype, 0) * VEHICLE_WEIGHTS.get(vtype, 1.0) for vtype in VEHICLE_WEIGHTS)
        return weighted_sum

    def get_raw_queue_length(self, direction):
        """Returns total unweighted vehicle count for a direction."""
        return sum(self.queues.get(direction, {}).values())

    def calculate_directional_pressure(self, direction_pair):
        """
        Calculates MaxPressure for direction pair ('NS' or 'EW').
        P(dir) = Inflow_Weighted_Queue - Downstream_Queue_Factor
        """
        if direction_pair == "NS":
            inflow = self.calculate_weighted_queue("N") + self.calculate_weighted_queue("S")
            outflow = (self.downstream_queues.get("N", 0) + self.downstream_queues.get("S", 0)) * 0.5
        else: # EW
            inflow = self.calculate_weighted_queue("E") + self.calculate_weighted_queue("W")
            outflow = (self.downstream_queues.get("E", 0) + self.downstream_queues.get("W", 0)) * 0.5

        pressure = max(0.0, inflow - outflow)
        return pressure

    def get_fairness_score(self, direction_pair):
        """
        Calculates starvation and waiting time fairness boost score.
        If max wait time exceeds threshold or cycles skipped >= threshold, score increases dramatically.
        """
        if direction_pair == "NS":
            max_wait = max(self.max_wait_time["N"], self.max_wait_time["S"])
            skipped_cycles = self.cycles_since_green["NS"]
        else:
            max_wait = max(self.max_wait_time["E"], self.max_wait_time["W"])
            skipped_cycles = self.cycles_since_green["EW"]

        fairness_score = 0.0
        if max_wait > MAX_WAIT_TIME_THRESHOLD:
            fairness_score += (max_wait - MAX_WAIT_TIME_THRESHOLD) * 2.0

        if skipped_cycles >= STARVATION_CYCLE_THRESHOLD:
            fairness_score += skipped_cycles * 15.0

        return fairness_score

    def generate_bid(self):
        """
        Generates an inter-agent priority bid for neighboring agents.
        Bids express requested corridor alignment and urgency.
        """
        p_ns = self.calculate_directional_pressure("NS")
        p_ew = self.calculate_directional_pressure("EW")

        preferred_dir = "NS" if p_ns >= p_ew else "EW"
        urgency = max(p_ns, p_ew) + max(self.get_fairness_score("NS"), self.get_fairness_score("EW"))

        has_emergency = any(
            self.queues[d].get("emergency", 0) > 0 for d in ["N", "S", "E", "W"]
        )

        bid = {
            "junction_id": self.junction_id,
            "preferred_dir": preferred_dir,
            "urgency": urgency,
            "has_emergency": has_emergency,
            "p_ns": p_ns,
            "p_ew": p_ew
        }
        self.last_bid_sent = bid
        return bid

    def receive_neighbor_bids(self, bids):
        """Receives and buffers bids sent by neighboring agents."""
        self.received_bids = bids

    def compute_neighbor_influence(self, direction_pair):
        """
        Computes network-wide corridor consensus score from neighboring agents.
        """
        influence = 0.0
        for n_id, bid in self.received_bids.items():
            if bid.get("preferred_dir") == direction_pair:
                influence += bid.get("urgency", 0.0) * NEIGHBOR_BID_WEIGHT
        return influence

    def decide_phase_action(self, strategy_type):
        """
        Decides the target green phase for the junction using specified strategy.
        Returns target_phase (PHASE_NS_GREEN or PHASE_EW_GREEN).
        """
        if strategy_type == "fixed_time":
            # Round robin: switch phase after MAX_GREEN_TIME
            if self.current_phase == PHASE_NS_GREEN and self.phase_duration >= 30:
                return PHASE_EW_GREEN
            elif self.current_phase == PHASE_EW_GREEN and self.phase_duration >= 30:
                return PHASE_NS_GREEN
            return self.current_phase

        elif strategy_type == "negotiated_directional":
            # MaxPressure only (Greedy directional pressure)
            if self.phase_duration < MIN_GREEN_TIME:
                return self.current_phase

            p_ns = self.calculate_directional_pressure("NS")
            p_ew = self.calculate_directional_pressure("EW")

            if p_ns > p_ew + 2.0:
                return PHASE_NS_GREEN
            elif p_ew > p_ns + 2.0:
                return PHASE_EW_GREEN
            return self.current_phase

        elif strategy_type == "fairness_aware":
            # Proposed Method: MaxPressure + Multi-Modal + Fairness + Neighbor Bid Negotiation
            if self.phase_duration < MIN_GREEN_TIME:
                return self.current_phase

            # Emergency Override Check
            ns_has_emergency = (self.queues["N"].get("emergency", 0) > 0 or self.queues["S"].get("emergency", 0) > 0)
            ew_has_emergency = (self.queues["E"].get("emergency", 0) > 0 or self.queues["W"].get("emergency", 0) > 0)

            if ns_has_emergency and not ew_has_emergency:
                return PHASE_NS_GREEN
            elif ew_has_emergency and not ns_has_emergency:
                return PHASE_EW_GREEN

            # Compute combined score: Local Pressure + Fairness Score + Neighbor Influence
            p_ns = self.calculate_directional_pressure("NS")
            p_ew = self.calculate_directional_pressure("EW")

            f_ns = self.get_fairness_score("NS")
            f_ew = self.get_fairness_score("EW")

            n_ns = self.compute_neighbor_influence("NS")
            n_ew = self.compute_neighbor_influence("EW")

            total_ns = p_ns + f_ns + n_ns
            total_ew = p_ew + f_ew + n_ew

            if self.phase_duration >= MAX_GREEN_TIME:
                # Force switch if max green reached
                return PHASE_EW_GREEN if self.current_phase == PHASE_NS_GREEN else PHASE_NS_GREEN

            if total_ns > total_ew + 1.5:
                return PHASE_NS_GREEN
            elif total_ew > total_ns + 1.5:
                return PHASE_EW_GREEN

            return self.current_phase

        return self.current_phase

    def step(self, strategy_type):
        """
        Executes one step (second) of the agent decision loop.
        Handles yellow transition phase timers and updates signal state.
        Returns active phase code.
        """
        self.phase_duration += 1

        # Check if currently in yellow transition
        if self.yellow_timer > 0:
            self.yellow_timer -= 1
            if self.yellow_timer == 0:
                # Yellow phase finished, switch to pending green phase
                self.current_phase = self.pending_phase
                self.phase_duration = 0
                self.pending_phase = None
            return self.current_phase

        # Ask strategy for desired green phase
        desired_green_phase = self.decide_phase_action(strategy_type)

        # Check if phase change is needed
        if desired_green_phase != self.current_phase:
            if self.current_phase == PHASE_NS_GREEN:
                self.current_phase = PHASE_NS_YELLOW
                self.yellow_timer = YELLOW_TIME
                self.pending_phase = PHASE_EW_GREEN
                self.cycles_since_green["NS"] = 0
                self.cycles_since_green["EW"] += 1
            elif self.current_phase == PHASE_EW_GREEN:
                self.current_phase = PHASE_EW_YELLOW
                self.yellow_timer = YELLOW_TIME
                self.pending_phase = PHASE_NS_GREEN
                self.cycles_since_green["EW"] = 0
                self.cycles_since_green["NS"] += 1

        return self.current_phase
