"""
Baseline Strategy 1: Fixed-Time Traffic Control
Cycles North-South and East-West phases on a fixed round-robin schedule (30s per green).
"""

class FixedTimeController:
    name = "Fixed-Time Control"
    description = "Static round-robin phase cycling with fixed green light duration (30 seconds)."

    @staticmethod
    def get_strategy_type():
        return "fixed_time"
