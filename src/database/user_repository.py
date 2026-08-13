from dataclasses import dataclass
from src.database.connection import get_connection


@dataclass
class UserRecord:
    xp: int
    level: int


DEFAULT_USER = UserRecord(xp=0, level=0)


class UserRepository:

    def fetch(self, user_id: str, guild_id: str) -> UserRecord:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ).fetchone()

        if row is None:
            return DEFAULT_USER

        return UserRecord(xp=row["xp"], level=row["level"])

    def save(self, user_id: str, guild_id: str, record: UserRecord) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO users (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp    = excluded.xp,
                    level = excluded.level
            """, (user_id, guild_id, record.xp, record.level))
