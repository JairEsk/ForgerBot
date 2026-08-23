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

    def _ongoing_minutes(self, key: str) -> int:
        """Minutes accumulated since the last checkpoint, not yet persisted."""
        checkpoint = self._active_sessions.get(key)

        if checkpoint is None:
            return 0

        return max(int((time.time() - checkpoint) / 60), 0)

    def _with_ongoing_minutes(self, record: VoiceExperienceRecord, ongoing_minutes: int) -> VoiceExperienceRecord:
        if ongoing_minutes == 0:
            return record

        return VoiceExperienceRecord(
            xp=record.xp,
            level=record.level,
            total_minutes=record.total_minutes + ongoing_minutes
        )

    def fetch_record(self, user_id: str, guild_id: str) -> VoiceExperienceRecord:
        record = self.voice_repository.fetch(user_id, guild_id)
        ongoing_minutes = self._ongoing_minutes(self._build_key(user_id, guild_id))

        return self._with_ongoing_minutes(record, ongoing_minutes)

    def fetch_top_records(self, guild_id: str, limit: int = 10) -> list[tuple[str, VoiceExperienceRecord]]:
        """Ranking including time from sessions still in progress, matching what /rank reports."""
        records: dict[str, VoiceExperienceRecord] = dict(
            self.voice_repository.fetch_top_users(guild_id, limit)
        )

        # Members currently connected may outrank the stored top once their
        # in-progress time is counted, so they have to be considered too.
        for key in self._active_sessions:
            session_guild_id, session_user_id = key.split(":", 1)

            if session_guild_id != guild_id or session_user_id in records:
                continue

            records[session_user_id] = self.voice_repository.fetch(session_user_id, guild_id)

        adjusted_records = [
            (
                user_id,
                self._with_ongoing_minutes(record, self._ongoing_minutes(self._build_key(user_id, guild_id)))
            )
            for user_id, record in records.items()
        ]

        adjusted_records.sort(key=lambda entry: entry[1].total_minutes, reverse=True)

        return adjusted_records[:limit]

