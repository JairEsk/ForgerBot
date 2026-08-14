import discord
from discord.ext import commands
from src.services.voice_service import VoiceService
from src.services.levelup_service import LevelUpService
from src.database.channel_repository import ChannelRepository


class Voice(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_service = VoiceService()
        self.levelup_service = LevelUpService()
        self.channel_repository = ChannelRepository()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
                if self.channel_repository.is_ignored(str(voice_channel.id), str(guild.id)):
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

        user_id = str(member.id)
        guild_id = str(member.guild.id)

        is_before_ignored = False
        if before.channel:
            is_before_ignored = self.channel_repository.is_ignored(str(before.channel.id), guild_id)

        is_after_ignored = False
        if after.channel:
            is_after_ignored = self.channel_repository.is_ignored(str(after.channel.id), guild_id)

        was_valid = before.channel is not None and not is_before_ignored
        is_valid = after.channel is not None and not is_after_ignored

        joined_valid = not was_valid and is_valid
        left_valid = was_valid and not is_valid

        if joined_valid:
            self.voice_service.start_session(user_id, guild_id)

        elif left_valid:
            session_result = self.voice_service.end_session(user_id, guild_id)

            if session_result is None:
                return

            if session_result.leveled_up:
                await self.levelup_service.announce_voice_levelup(member, session_result.new_level)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
