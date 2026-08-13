import time
from dataclasses import dataclass
from src.database.voice_repository import VoiceRepository

MINIMUM_MINUTES_TO_GRANT_XP = 1


@dataclass
class VoiceSessionResult:
    minutes_spent: int
    xp_earned: int


class VoiceService:

    def __init__(self):
        self.voice_repository = VoiceRepository()
        self._active_sessions: dict[str, float] = {}

    def _build_key(self, user_id: str, guild_id: str) -> str:
        return f"{guild_id}:{user_id}"

    def start_session(self, user_id: str, guild_id: str) -> None:
        key = self._build_key(user_id, guild_id)
        self._active_sessions[key] = time.time()

    def end_session(self, user_id: str, guild_id: str) -> VoiceSessionResult | None:
        key = self._build_key(user_id, guild_id)

        if key not in self._active_sessions:
            return None

        session_start = self._active_sessions.pop(key)
        minutes_spent = int((time.time() - session_start) / 60)

        if minutes_spent < MINIMUM_MINUTES_TO_GRANT_XP:
            return None

        from src.services.experience_service import XP_PER_VOICE_MINUTE
        xp_earned = minutes_spent * XP_PER_VOICE_MINUTE

        self.voice_repository.add_minutes(user_id, guild_id, minutes_spent)

        return VoiceSessionResult(minutes_spent=minutes_spent, xp_earned=xp_earned)

    def fetch_total_minutes(self, user_id: str, guild_id: str) -> int:
        return self.voice_repository.fetch(user_id, guild_id).total_minutes
