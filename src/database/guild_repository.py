from dataclasses import dataclass
from src.database.connection import get_connection

DEFAULT_COOLDOWN = 60
DEFAULT_LEVELUP_MESSAGE = "🎉 {user} just reached level **{level}**!"


@dataclass
class GuildSettings:
    cooldown: int
    levelup_message: str
    levelup_channel_id: str | None


DEFAULT_SETTINGS = GuildSettings(
    cooldown=DEFAULT_COOLDOWN,
    levelup_message=DEFAULT_LEVELUP_MESSAGE,
    levelup_channel_id=None
)


class GuildRepository:

    def fetch_settings(self, guild_id: str) -> GuildSettings:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT cooldown, levelup_message, levelup_channel_id FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            ).fetchone()

        if row is None:
            return DEFAULT_SETTINGS

        return GuildSettings(
            cooldown=row["cooldown"],
            levelup_message=row["levelup_message"],
            levelup_channel_id=row["levelup_channel_id"]
        )

    def save_cooldown(self, guild_id: str, cooldown: int) -> None:
        current = self.fetch_settings(guild_id)
        self._save(guild_id, cooldown, current.levelup_message, current.levelup_channel_id)

    def save_levelup_message(self, guild_id: str, levelup_message: str) -> None:
        current = self.fetch_settings(guild_id)
        self._save(guild_id, current.cooldown, levelup_message, current.levelup_channel_id)

    def save_levelup_channel(self, guild_id: str, channel_id: str | None) -> None:
        current = self.fetch_settings(guild_id)
        self._save(guild_id, current.cooldown, current.levelup_message, channel_id)

    def _save(self, guild_id: str, cooldown: int, levelup_message: str, levelup_channel_id: str | None) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, cooldown, levelup_message, levelup_channel_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    cooldown           = excluded.cooldown,
                    levelup_message    = excluded.levelup_message,
                    levelup_channel_id = excluded.levelup_channel_id
            """, (guild_id, cooldown, levelup_message, levelup_channel_id))
