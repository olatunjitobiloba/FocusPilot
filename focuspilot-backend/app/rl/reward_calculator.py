"""
Reward Calculator - computes reward signal from intervention outcomes.

Reward scale:
    +1.0  User focused 20+ more minutes after intervention
    +0.5  User focused 5-20 more minutes
     0.0  No measurable change in behavior
    -0.5  Distraction increased after intervention
    -1.0  User ended session after intervention

We measure outcome by comparing:
    - Focus score before vs after intervention
    - Distraction ratio before vs after
    - Whether session continued
"""

from typing import Dict


class RewardCalculator:

    # Reward thresholds
    GREAT_FOCUS_GAIN = 20  # minutes of additional focus
    GOOD_FOCUS_GAIN = 5    # minutes of additional focus

    REWARD_GREAT = 1.0
    REWARD_GOOD = 0.5
    REWARD_NEUTRAL = 0.0
    REWARD_BAD = -0.5
    REWARD_TERRIBLE = -1.0

    def calculate(
        self,
        focus_before: float,
        focus_after: float,
        distraction_before: float,
        distraction_after: float,
        session_continued: bool,
        minutes_after_intervention: float,
    ) -> Dict:
        """
        Calculate reward from intervention outcome.

        Args:
            focus_before: Focus score before intervention (0-10)
            focus_after: Focus score after intervention (0-10)
            distraction_before: Distraction ratio before (0-1)
            distraction_after: Distraction ratio after (0-1)
            session_continued: Did session continue after intervention?
            minutes_after_intervention: How long user focused after intervention

        Returns:
            {'reward': float, 'outcome': str, 'explanation': str}
        """
        # Session ended immediately after intervention
        if not session_continued:
            return {
                "reward": self.REWARD_TERRIBLE,
                "outcome": "session_ended",
                "explanation": "User ended session after intervention",
            }

        # Great outcome - focused 20+ more minutes
        if minutes_after_intervention >= self.GREAT_FOCUS_GAIN:
            return {
                "reward": self.REWARD_GREAT,
                "outcome": "focused_more",
                "explanation": (
                    f"User focused {round(minutes_after_intervention)}m "
                    f"after intervention"
                ),
            }

        # Good outcome - focused 5-20 more minutes
        if minutes_after_intervention >= self.GOOD_FOCUS_GAIN:
            return {
                "reward": self.REWARD_GOOD,
                "outcome": "focused_more",
                "explanation": (
                    f"User focused {round(minutes_after_intervention)}m "
                    f"after intervention"
                ),
            }

        # Bad outcome - distraction increased
        if distraction_after > distraction_before + 0.15:
            return {
                "reward": self.REWARD_BAD,
                "outcome": "distracted_more",
                "explanation": (
                    "Distraction increased from "
                    f"{round(distraction_before * 100)}% to "
                    f"{round(distraction_after * 100)}%"
                ),
            }

        # Neutral - no meaningful change
        return {
            "reward": self.REWARD_NEUTRAL,
            "outcome": "no_change",
            "explanation": "No measurable change in behavior",
        }

    def outcome_label(self, outcome: str) -> str:
        """Human-readable outcome label."""
        labels = {
            "focused_more": "Focused More",
            "no_change": "No Change",
            "distracted_more": "Distracted More",
            "session_ended": "Session Ended",
        }
        return labels.get(outcome, outcome)

    def reward_label(self, reward: float) -> str:
        """Human-readable reward label."""
        if reward >= 1.0:
            return "Excellent"
        if reward >= 0.5:
            return "Good"
        if reward >= 0.0:
            return "Neutral"
        if reward >= -0.5:
            return "Poor"
        return "Bad"


reward_calculator = RewardCalculator()
