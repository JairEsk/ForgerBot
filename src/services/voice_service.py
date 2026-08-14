import time
from dataclasses import dataclass
from src.database.voice_repository import VoiceRepository, VoiceExperienceRecord
from src.services.experience_service import ExperienceService, XP_PER_VOICE_MINUTE

MINIMUM_MINUTES_TO_GRANT_XP = 1


@dataclass
class VoiceSessionResult:
    minutes_spent: int
    xp_earned: int
    new_level: int
    leveled_up: bool


class VoiceService:

    def __init__(self):
        self.voice_repository = VoiceRepository()
        self.experience_service = ExperienceService()
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

        xp_earned = minutes_spent * XP_PER_VOICE_MINUTE

        current_record = self.voice_repository.fetch(user_id, guild_id)
        result = self.experience_service.compute_grant(current_record.xp, current_record.level, xp_earned)

        updated_record = VoiceExperienceRecord(
            xp=result.xp,
            level=result.level,
            total_minutes=current_record.total_minutes + minutes_spent
        )
        self.voice_repository.save(user_id, guild_id, updated_record)

        return VoiceSessionResult(
            minutes_spent=minutes_spent,
            xp_earned=xp_earned,
            new_level=result.level,
            leveled_up=result.leveled_up
        )

    def fetch_record(self, user_id: str, guild_id: str) -> VoiceExperienceRecord:
        record = self.voice_repository.fetch(user_id, guild_id)
        key = self._build_key(user_id, guild_id)
        
        if key in self._active_sessions:
            session_start = self._active_sessions[key]
            ongoing_minutes = int((time.time() - session_start) / 60)
            
            if ongoing_minutes > 0:
                ongoing_xp = ongoing_minutes * XP_PER_VOICE_MINUTE
                result = self.experience_service.compute_grant(record.xp, record.level, ongoing_xp)
                
                return VoiceExperienceRecord(
                    xp=result.xp,
                    level=result.level,
                    total_minutes=record.total_minutes + ongoing_minutes
                )
                
        return record
