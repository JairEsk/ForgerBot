import random
from dataclasses import dataclass

XP_MINIMUM_PER_MESSAGE = 15
XP_MAXIMUM_PER_MESSAGE = 25
XP_PER_VOICE_MINUTE    = 10
XP_BASE_PER_LEVEL      = 100


@dataclass
class ExperienceResult:
    xp: int
    level: int
    leveled_up: bool


class ExperienceService:

    def calculate_xp_required(self, level: int) -> int:
        return XP_BASE_PER_LEVEL * (level ** 2)

    def random_message_xp(self) -> int:
        return random.randint(XP_MINIMUM_PER_MESSAGE, XP_MAXIMUM_PER_MESSAGE)

    def compute_grant(self, current_xp: int, current_level: int, amount: int) -> ExperienceResult:
        new_xp = current_xp + amount
        new_level = current_level
        leveled_up = False

        xp_required = self.calculate_xp_required(new_level + 1)
        if new_xp >= xp_required:
            new_level += 1
            leveled_up = True

        return ExperienceResult(xp=new_xp, level=new_level, leveled_up=leveled_up)
