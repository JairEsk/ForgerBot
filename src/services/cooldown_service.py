import time
from src.database.guild_repository import GuildRepository

MINIMUM_COOLDOWN_SECONDS = 10
MAXIMUM_COOLDOWN_SECONDS = 3600


class CooldownService:

    def __init__(self):
        self.guild_repository = GuildRepository()
        self._last_message_timestamps: dict[str, float] = {}

    def _build_key(self, user_id: str, guild_id: str) -> str:
        return f"{guild_id}:{user_id}"

    def is_on_cooldown(self, user_id: str, guild_id: str) -> bool:
        key = self._build_key(user_id, guild_id)
        last_timestamp = self._last_message_timestamps.get(key, 0)
        settings = self.guild_repository.fetch_settings(guild_id)
        return (time.time() - last_timestamp) < settings.cooldown

    def register(self, user_id: str, guild_id: str) -> None:
        key = self._build_key(user_id, guild_id)
        self._last_message_timestamps[key] = time.time()
