from dataclasses import dataclass
from src.database.connection import get_connection


@dataclass
class VoiceRecord:
    total_minutes: int


class VoiceRepository:

    def fetch(self, user_id: str, guild_id: str) -> VoiceRecord:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT total_minutes FROM voice_sessions WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ).fetchone()

        if row is None:
            return VoiceRecord(total_minutes=0)

        return VoiceRecord(total_minutes=row["total_minutes"])

    def add_minutes(self, user_id: str, guild_id: str, minutes: int) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO voice_sessions (user_id, guild_id, total_minutes)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    total_minutes = total_minutes + excluded.total_minutes
            """, (user_id, guild_id, minutes))
