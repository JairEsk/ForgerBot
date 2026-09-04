import discord
from discord.ext import commands, tasks
from src.services.voice_service import VoiceService
from src.database.channel_repository import ChannelRepository
from src.database.guild_repository import GuildRepository, GuildSettings

CHECKPOINT_INTERVAL_MINUTES = 1


class Voice(commands.Cog):

    def __init__(self, bot: commands.Bot, voice_service: VoiceService):
        self.bot = bot
        self.voice_service = voice_service
        self.channel_repository = ChannelRepository()
        self.guild_repository = GuildRepository()
        self.checkpoint_sessions.start()

    async def cog_unload(self) -> None:
        self.checkpoint_sessions.cancel()
        self.voice_service.flush_sessions()

    @tasks.loop(minutes=CHECKPOINT_INTERVAL_MINUTES)
    async def checkpoint_sessions(self) -> None:
        self.voice_service.flush_sessions()

    @checkpoint_sessions.before_loop
    async def before_checkpoint_sessions(self) -> None:
        await self.bot.wait_until_ready()

    def _is_channel_ignored(
        self,
        channel: discord.abc.Connectable | None,
        guild: discord.Guild,
        settings: GuildSettings
    ) -> bool:
        if channel is None:
            return True

        if settings.auto_ignore_afk and guild.afk_channel is not None and channel.id == guild.afk_channel.id:
            return True

        guild_id = str(guild.id)
        return self.channel_repository.is_ignored(str(channel.id), guild_id)

    def _is_voice_state_valid(
        self,
        state: discord.VoiceState,
        guild: discord.Guild,
        settings: GuildSettings
    ) -> bool:
        if state.channel is None:
            return False

        if settings.auto_ignore_afk and state.afk:
            return False

        return not self._is_channel_ignored(state.channel, guild, settings)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            settings = self.guild_repository.fetch_settings(str(guild.id))
            for voice_channel in guild.voice_channels:
                if self._is_channel_ignored(voice_channel, guild, settings):
                    continue
                for member in voice_channel.members:
                    if not member.bot:
                        self.voice_service.start_session(str(member.id), str(guild.id))

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ) -> None:
        if member.bot:
            return

        if before.channel == after.channel:
            return

        user_id = str(member.id)
        guild_id = str(member.guild.id)
        settings = self.guild_repository.fetch_settings(guild_id)

        was_valid = self._is_voice_state_valid(before, member.guild, settings)
        is_valid = self._is_voice_state_valid(after, member.guild, settings)

        joined_valid = not was_valid and is_valid
        left_valid = was_valid and not is_valid

        if joined_valid:
            self.voice_service.start_session(user_id, guild_id)

        elif left_valid:
            self.voice_service.end_session(user_id, guild_id)
