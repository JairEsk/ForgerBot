import time
from dataclasses import dataclass
from src.database.voice_repository import VoiceRepository, VoiceExperienceRecord

MINIMUM_MINUTES_TO_GRANT_XP = 1


@dataclass
class VoiceSessionResult:
    minutes_spent: int


class VoiceService:

    def __init__(self):
        self.voice_repository = VoiceRepository()
        self._active_sessions: dict[str, float] = {}

    def _build_key(self, user_id: str, guild_id: str) -> str:
        return f"{guild_id}:{user_id}"

    def start_session(self, user_id: str, guild_id: str) -> None:
        key = self._build_key(user_id, guild_id)
        self._active_sessions[key] = time.time()

    def _consume_elapsed_minutes(self, key: str) -> int:
        checkpoint = self._active_sessions[key]
        minutes_spent = int((time.time() - checkpoint) / 60)

        if minutes_spent > 0:
            self._active_sessions[key] = checkpoint + minutes_spent * 60

        return minutes_spent

    def _award_minutes(self, user_id: str, guild_id: str, minutes_spent: int) -> VoiceSessionResult:
        current_record = self.voice_repository.fetch(user_id, guild_id)

        updated_record = VoiceExperienceRecord(
            xp=current_record.xp,
            level=current_record.level,
            total_minutes=current_record.total_minutes + minutes_spent
        )
        self.voice_repository.save(user_id, guild_id, updated_record)

        return VoiceSessionResult(minutes_spent=minutes_spent)

    def end_session(self, user_id: str, guild_id: str) -> VoiceSessionResult | None:
        key = self._build_key(user_id, guild_id)

        if key not in self._active_sessions:
            return None

        minutes_spent = self._consume_elapsed_minutes(key)
        self._active_sessions.pop(key)

        if minutes_spent < MINIMUM_MINUTES_TO_GRANT_XP:
            return None

        return self._award_minutes(user_id, guild_id, minutes_spent)

    def flush_sessions(self) -> list[tuple[str, str, VoiceSessionResult]]:
        """Persist the time accumulated so far by every active session without ending it."""
        flushed = []

        for key in list(self._active_sessions):
            guild_id, user_id = key.split(":", 1)
            minutes_spent = self._consume_elapsed_minutes(key)

            if minutes_spent < MINIMUM_MINUTES_TO_GRANT_XP:
                continue

            flushed.append((user_id, guild_id, self._award_minutes(user_id, guild_id, minutes_spent)))

        return flushed

    def fetch_record(self, user_id: str, guild_id: str) -> VoiceExperienceRecord:
        record = self.voice_repository.fetch(user_id, guild_id)
        key = self._build_key(user_id, guild_id)
        
        if key in self._active_sessions:
            session_start = self._active_sessions[key]
            ongoing_minutes = int((time.time() - session_start) / 60)
            
            if ongoing_minutes > 0:
                return VoiceExperienceRecord(
                    xp=record.xp,
                    level=record.level,
                    total_minutes=record.total_minutes + ongoing_minutes
                )
                
        return record

