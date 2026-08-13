import discord
from discord.ext import commands
from src.services.voice_service import VoiceService
from src.services.experience_service import ExperienceService
from src.database.guild_repository import GuildRepository


class Voice(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_service = VoiceService()
        self.experience_service = ExperienceService()
        self.guild_repository = GuildRepository()

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

            xp_result = self.experience_service.grant_xp(user_id, guild_id, session_result.xp_earned)

            if xp_result.leveled_up:
                announcement_channel = member.guild.system_channel
                if announcement_channel:
                    await self._send_levelup_message(announcement_channel, member, xp_result.record.level, guild_id)

    async def _send_levelup_message(
        self,
        channel: discord.TextChannel,
        member: discord.Member,
        new_level: int,
        guild_id: str
    ) -> None:
        settings = self.guild_repository.fetch_settings(guild_id)
        formatted_message = settings.levelup_message.replace(
            "{user}", member.mention
        ).replace(
            "{level}", str(new_level)
        )
        await channel.send(formatted_message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
