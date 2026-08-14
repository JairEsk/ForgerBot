from dataclasses import dataclass
from src.database.connection import get_connection


@dataclass
class VoiceExperienceRecord:
    xp: int
    level: int
    total_minutes: int


DEFAULT_RECORD = VoiceExperienceRecord(xp=0, level=0, total_minutes=0)


class VoiceRepository:

    def fetch(self, user_id: str, guild_id: str) -> VoiceExperienceRecord:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT xp, level, total_minutes FROM voice_experience WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ).fetchone()

        if row is None:
            return DEFAULT_RECORD

        return VoiceExperienceRecord(xp=row["xp"], level=row["level"], total_minutes=row["total_minutes"])

    def save(self, user_id: str, guild_id: str, record: VoiceExperienceRecord) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO voice_experience (user_id, guild_id, xp, level, total_minutes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp            = excluded.xp,
                    level         = excluded.level,
                    total_minutes = excluded.total_minutes
            """, (user_id, guild_id, record.xp, record.level, record.total_minutes))
