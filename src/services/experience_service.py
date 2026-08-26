import random
from dataclasses import dataclass
from math import isqrt

XP_MINIMUM_PER_MESSAGE = 15
XP_MAXIMUM_PER_MESSAGE = 25
XP_BASE_PER_LEVEL      = 100


@dataclass
class ExperienceResult:
    xp: int
    previous_level: int
    level: int

    @property
    def leveled_up(self) -> bool:
        return self.level > self.previous_level


def calculate_xp_required(level: int) -> int:
    """Return the cumulative XP threshold for ``level``."""
    if level < 0:
        raise ValueError("level cannot be negative")
    return XP_BASE_PER_LEVEL * (level ** 2)


def calculate_level(xp: int) -> int:
    """Derive the canonical level from cumulative XP.

    XP is the source of truth. Keeping this calculation deterministic prevents a
    persisted level column from drifting independently after a restart, migration,
    or concurrent update.
    """
    if xp < 0:
        raise ValueError("xp cannot be negative")
    return isqrt(xp // XP_BASE_PER_LEVEL)


class ExperienceService:

    def calculate_xp_required(self, level: int) -> int:
        return calculate_xp_required(level)

    def calculate_level(self, xp: int) -> int:
        return calculate_level(xp)

    def random_message_xp(self) -> int:
        return random.randint(XP_MINIMUM_PER_MESSAGE, XP_MAXIMUM_PER_MESSAGE)

    def compute_grant(self, current_xp: int, amount: int) -> ExperienceResult:
        if amount < 0:
            raise ValueError("XP grant cannot be negative")

        previous_level = self.calculate_level(current_xp)
        new_xp = current_xp + amount
        new_level = self.calculate_level(new_xp)

        return ExperienceResult(
            xp=new_xp,
            previous_level=previous_level,
            level=new_level
        )
