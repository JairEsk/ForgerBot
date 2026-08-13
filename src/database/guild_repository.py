from dataclasses import dataclass
from src.database.connection import get_connection

DEFAULT_COOLDOWN = 60
DEFAULT_LEVELUP_MESSAGE = "🎉 {user} just reached level **{level}**!"


@dataclass
class GuildSettings:
    cooldown: int
    levelup_message: str


DEFAULT_SETTINGS = GuildSettings(
    cooldown=DEFAULT_COOLDOWN,
    levelup_message=DEFAULT_LEVELUP_MESSAGE
)


class GuildRepository:

    def fetch_settings(self, guild_id: str) -> GuildSettings:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT cooldown, levelup_message FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            ).fetchone()

        if row is None:
            return DEFAULT_SETTINGS

        return GuildSettings(cooldown=row["cooldown"], levelup_message=row["levelup_message"])

    def save_cooldown(self, guild_id: str, cooldown: int) -> None:
        current_settings = self.fetch_settings(guild_id)
        self._save(guild_id, cooldown, current_settings.levelup_message)

    def save_levelup_message(self, guild_id: str, levelup_message: str) -> None:
        current_settings = self.fetch_settings(guild_id)
        self._save(guild_id, current_settings.cooldown, levelup_message)

    def _save(self, guild_id: str, cooldown: int, levelup_message: str) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, cooldown, levelup_message)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    cooldown        = excluded.cooldown,
                    levelup_message = excluded.levelup_message
            """, (guild_id, cooldown, levelup_message))
