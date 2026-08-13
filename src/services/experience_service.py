import random
from dataclasses import dataclass
from src.database.user_repository import UserRepository, UserRecord

XP_MINIMUM_PER_MESSAGE = 15
XP_MAXIMUM_PER_MESSAGE = 25
XP_PER_VOICE_MINUTE    = 10
XP_BASE_PER_LEVEL      = 100


@dataclass
class ExperienceResult:
    record: UserRecord
    leveled_up: bool


class ExperienceService:

    def __init__(self):
        self.user_repository = UserRepository()

    def calculate_xp_required(self, level: int) -> int:
        return XP_BASE_PER_LEVEL * (level ** 2)

    def random_message_xp(self) -> int:
        return random.randint(XP_MINIMUM_PER_MESSAGE, XP_MAXIMUM_PER_MESSAGE)

    def grant_xp(self, user_id: str, guild_id: str, amount: int) -> ExperienceResult:
        current_record = self.user_repository.fetch(user_id, guild_id)

        new_xp = current_record.xp + amount
        new_level = current_record.level
        leveled_up = False

        xp_required = self.calculate_xp_required(new_level + 1)
        if new_xp >= xp_required:
            new_level += 1
            leveled_up = True

        updated_record = UserRecord(xp=new_xp, level=new_level)
        self.user_repository.save(user_id, guild_id, updated_record)

        return ExperienceResult(record=updated_record, leveled_up=leveled_up)
