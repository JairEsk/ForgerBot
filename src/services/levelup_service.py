import logging
import discord
from src.database.guild_repository import (
    GuildRepository,
    GuildSettings,
    LEVELUP_MODE_CURRENT,
    LEVELUP_MODE_CUSTOM,
    LEVELUP_MODE_DISABLED,
    LEVELUP_MODE_DM,
)

logger = logging.getLogger(__name__)


class LevelUpService:

    def __init__(self):
        self.guild_repository = GuildRepository()

    async def resolve_custom_channel(self, guild: discord.Guild, channel_id: str) -> discord.TextChannel | None:
        """Resolves the custom level-up channel. Returns None if invalid or inaccessible."""
        channel = guild.get_channel(int(channel_id))

        if channel is None:
            try:
                channel = await guild.fetch_channel(int(channel_id))
            except discord.NotFound:
                logger.warning(
                    "Level-up channel %s no longer exists in guild %s; skipping announcement.",
                    channel_id, guild.id
                )
                return None
            except discord.Forbidden:
                logger.warning(
                    "Missing access to level-up channel %s in guild %s; skipping announcement.",
                    channel_id, guild.id
                )
                return None

        if not isinstance(channel, discord.TextChannel):
            logger.warning(
                "Level-up channel %s in guild %s is not a text channel; skipping announcement.",
                channel_id, guild.id
            )
            return None

        return channel

    def _format_message(self, settings: GuildSettings, member: discord.Member, new_level: int) -> str:
        return settings.levelup_message.replace(
            "{user}", member.mention
        ).replace(
            "{level}", str(new_level)
        )

    async def announce_text_levelup(self, message: discord.Message, new_level: int) -> None:
        settings = self.guild_repository.fetch_settings(str(message.guild.id))

        if settings.levelup_mode == LEVELUP_MODE_DISABLED:
            return

        formatted_message = self._format_message(settings, message.author, new_level)

        if settings.levelup_mode == LEVELUP_MODE_DM:
            try:
                await message.author.send(formatted_message)
            except discord.Forbidden:
                logger.info(
                    "Could not DM level-up to user %s (DMs closed).", message.author.id
                )
            return

        target_channel = message.channel

        if settings.levelup_mode == LEVELUP_MODE_CUSTOM:
            resolved_channel = await self.resolve_custom_channel(message.guild, settings.levelup_channel_id)
            if resolved_channel is None:
                # Strict silence if the custom channel is unavailable.
                return
            target_channel = resolved_channel

        try:
            await target_channel.send(formatted_message)
        except discord.Forbidden:
            logger.warning(
                "Missing send permission in channel %s of guild %s; level-up not announced.",
                target_channel.id, message.guild.id
            )
