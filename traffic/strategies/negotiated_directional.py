"""
Baseline Strategy 2: Negotiated Directional Control (Greedy MaxPressure)
Dynamically allocates green time to the direction with highest local queue pressure.
"""

class NegotiatedDirectionalController:
    name = "Negotiated Directional"
    description = "Greedy directional phase switching based on local incoming queue pressure."

    @staticmethod
    def get_strategy_type():
        return "negotiated_directional"
