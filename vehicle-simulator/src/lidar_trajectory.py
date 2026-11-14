"""Fixed LiDAR distance ladder for repeatable obstruction scenarios.

The provider moves one rung per tick: up toward the hold while an
obstruction is active, back down toward clear road otherwise. Health is
never decided here; Velocitas classifies the published distance.
"""

LADDER = (35.0, 20.0, 8.0, 3.0)
HOLD_STEP = len(LADDER) - 1


def next_step(step: int, obstructed: bool) -> int:
    if obstructed:
        return min(step + 1, HOLD_STEP)
    return max(step - 1, 0)


def distance(step: int) -> float:
    return LADDER[step]
