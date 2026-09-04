from dataclasses import dataclass
from src.database.connection import get_connection

DEFAULT_COOLDOWN = 60
DEFAULT_LEVELUP_MESSAGE = "🎉 {user} just reached level **{level}**!"

LEVELUP_MODE_DISABLED = "disabled"
LEVELUP_MODE_CURRENT = "current"
LEVELUP_MODE_CUSTOM = "custom"
LEVELUP_MODE_DM = "dm"

VALID_LEVELUP_MODES = {
    LEVELUP_MODE_DISABLED,
    LEVELUP_MODE_CURRENT,
    LEVELUP_MODE_CUSTOM,
    LEVELUP_MODE_DM,
}

DEFAULT_LEVELUP_MODE = LEVELUP_MODE_CURRENT
DEFAULT_AUTO_IGNORE_AFK = True


@dataclass
class GuildSettings:
    cooldown: int
    levelup_message: str
    levelup_channel_id: str | None
    levelup_mode: str
    auto_ignore_afk: bool = DEFAULT_AUTO_IGNORE_AFK


DEFAULT_SETTINGS = GuildSettings(
    cooldown=DEFAULT_COOLDOWN,
    levelup_message=DEFAULT_LEVELUP_MESSAGE,
    levelup_channel_id=None,
    levelup_mode=DEFAULT_LEVELUP_MODE,
    auto_ignore_afk=DEFAULT_AUTO_IGNORE_AFK
)


class GuildRepository:

    def fetch_settings(self, guild_id: str) -> GuildSettings:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT cooldown, levelup_message, levelup_channel_id, levelup_mode, auto_ignore_afk FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            ).fetchone()

        if row is None:
            return DEFAULT_SETTINGS

        mode = row["levelup_mode"]
        if mode not in VALID_LEVELUP_MODES:
            mode = DEFAULT_LEVELUP_MODE

        # "custom" without a channel is unresolvable, so fall back to the
        # channel where the level-up happened instead of dropping the message.
        if mode == LEVELUP_MODE_CUSTOM and row["levelup_channel_id"] is None:
            mode = LEVELUP_MODE_CURRENT

        auto_ignore_afk = bool(row["auto_ignore_afk"]) if "auto_ignore_afk" in row.keys() else DEFAULT_AUTO_IGNORE_AFK

        return GuildSettings(
            cooldown=row["cooldown"],
            levelup_message=row["levelup_message"],
            levelup_channel_id=row["levelup_channel_id"],
            levelup_mode=mode,
            auto_ignore_afk=auto_ignore_afk
        )

    def save_cooldown(self, guild_id: str, cooldown: int) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, cooldown)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    cooldown = excluded.cooldown
            """, (guild_id, cooldown))

    def save_levelup_message(self, guild_id: str, levelup_message: str) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, levelup_message)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    levelup_message = excluded.levelup_message
            """, (guild_id, levelup_message))

    def save_levelup_channel(self, guild_id: str, channel_id: str) -> None:
        """Pick a custom announcement channel. Selecting a channel implies custom mode."""
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, levelup_channel_id, levelup_mode)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    levelup_channel_id = excluded.levelup_channel_id,
                    levelup_mode = excluded.levelup_mode
            """, (guild_id, channel_id, LEVELUP_MODE_CUSTOM))

    def save_levelup_mode(self, guild_id: str, mode: str) -> None:
        """Switch announcement mode. The saved channel is kept so switching back restores it."""
        if mode not in VALID_LEVELUP_MODES:
            raise ValueError(f"Unknown level-up mode: {mode}")

        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, levelup_mode)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    levelup_mode = excluded.levelup_mode
            """, (guild_id, mode))

    def save_auto_ignore_afk(self, guild_id: str, enabled: bool) -> None:
        with get_connection() as connection:
            connection.execute("""
                INSERT INTO guild_settings (guild_id, auto_ignore_afk)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    auto_ignore_afk = excluded.auto_ignore_afk
            """, (guild_id, 1 if enabled else 0))

