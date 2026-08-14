import discord
from discord.ext import commands
from src.services.voice_service import VoiceService
from src.services.levelup_service import LevelUpService


class Voice(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_service = VoiceService()
        self.levelup_service = LevelUpService()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            for voice_channel in guild.voice_channels:
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

        joined_voice = before.channel is None and after.channel is not None
        left_voice = before.channel is not None and after.channel is None

        if joined_voice:
            self.voice_service.start_session(user_id, guild_id)

        elif left_voice:
            session_result = self.voice_service.end_session(user_id, guild_id)

            if session_result is None:
                return

            if session_result.leveled_up:
                await self.levelup_service.announce_voice_levelup(member, session_result.new_level)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
