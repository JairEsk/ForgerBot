from dataclasses import dataclass
from src.database.connection import get_connection
from src.services.experience_service import ExperienceResult, ExperienceService, calculate_level


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

        xp = row["xp"]
        return TextExperienceRecord(xp=xp, level=calculate_level(xp))

    def save(self, user_id: str, guild_id: str, record: TextExperienceRecord) -> None:
        canonical_level = calculate_level(record.xp)
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO text_experience (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp    = excluded.xp,
                    level = excluded.level
            """, (user_id, guild_id, record.xp, canonical_level))

    def grant_xp(
        self,
        user_id: str,
        guild_id: str,
        amount: int,
        experience_service: ExperienceService
    ) -> ExperienceResult:
        """Atomically grant XP and persist its derived level.

        ``BEGIN IMMEDIATE`` serializes grants for the same SQLite database. This
        avoids the lost-update window created by a separate fetch followed by a
        save when more than one bot process handles activity.
        """
        if amount < 0:
            raise ValueError("XP grant cannot be negative")

        with get_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT xp FROM text_experience WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ).fetchone()
            current_xp = row["xp"] if row is not None else 0
            result = experience_service.compute_grant(current_xp, amount)

            connection.execute("""
                INSERT INTO text_experience (user_id, guild_id, xp, level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    xp    = excluded.xp,
                    level = excluded.level
            """, (user_id, guild_id, result.xp, result.level))

        return result

    def fetch_top_users(self, guild_id: str, limit: int = 10) -> list[tuple[str, TextExperienceRecord]]:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT user_id, xp, level FROM text_experience WHERE guild_id = ? ORDER BY xp DESC LIMIT ?",
                (guild_id, limit)
            ).fetchall()

        return [
            (
                row["user_id"],
                TextExperienceRecord(xp=row["xp"], level=calculate_level(row["xp"]))
            )
            for row in rows
        ]
