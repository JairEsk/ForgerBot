import discord
from src.database.guild_repository import GuildRepository, GuildSettings


class LevelUpService:

    def __init__(self):
        self.guild_repository = GuildRepository()

    def get_configured_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        settings = self.guild_repository.fetch_settings(str(guild.id))

        if settings.levelup_channel_id is not None:
            return guild.get_channel(int(settings.levelup_channel_id))

        return None

    def _format_message(self, settings: GuildSettings, member: discord.Member, new_level: int) -> str:
        return settings.levelup_message.replace(
            "{user}", member.mention
        ).replace(
            "{level}", str(new_level)
        )

    async def announce_text_levelup(self, message: discord.Message, new_level: int) -> None:
        settings = self.guild_repository.fetch_settings(str(message.guild.id))
        formatted_message = self._format_message(settings, message.author, new_level)
        
        target_channel = self.get_configured_channel(message.guild) or message.channel
        await target_channel.send(formatted_message)

    async def announce_voice_levelup(self, member: discord.Member, new_level: int) -> None:
        settings = self.guild_repository.fetch_settings(str(member.guild.id))
        formatted_message = self._format_message(settings, member, new_level)
        
        target_channel = self.get_configured_channel(member.guild)

        if target_channel:
            await target_channel.send(formatted_message)

