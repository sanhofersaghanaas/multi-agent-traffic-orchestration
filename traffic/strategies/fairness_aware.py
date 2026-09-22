"""
Proposed Method: Dynamic Agentic Fairness-Aware Multi-Modal Traffic Control
Combines MaxPressure, multi-modal priority weighting (emergency/bus boost),
inter-agent priority bid negotiation, and starvation waiting-time fairness caps.
"""

class FairnessAwareController:
    name = "Fairness-Aware Agentic (Proposed)"
    description = "Autonomous AI Agent negotiation with MaxPressure, multi-modal vehicle priority, green wave bidding, and starvation fairness caps."

    @staticmethod
    def get_strategy_type():
        return "fairness_aware"
