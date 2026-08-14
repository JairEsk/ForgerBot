from dataclasses import dataclass
from src.database.connection import get_connection


@dataclass
class TextExperienceRecord:
    xp: int
    level: int


DEFAULT_RECORD = TextExperienceRecord(xp=0, level=0)


class UserRepository:

    def fetch(self, user_id: str, guild_id: str) -> TextExperienceRecord:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT xp, level FROM text_experience WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ).fetchone()

        if row is None:
            return DEFAULT_RECORD

        return TextExperienceRecord(xp=row["xp"], level=row["level"])

    def save(self, user_id: str, guild_id: str, record: TextExperienceRecord) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO text_experience (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp    = excluded.xp,
                    level = excluded.level
            """, (user_id, guild_id, record.xp, record.level))
