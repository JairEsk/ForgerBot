import discord
from discord.ext import commands
from src.services.experience_service import ExperienceService
from src.services.cooldown_service import CooldownService
from src.database.channel_repository import ChannelRepository
from src.database.guild_repository import GuildRepository


class Leveling(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.experience_service = ExperienceService()
        self.cooldown_service = CooldownService()
        self.channel_repository = ChannelRepository()
        self.guild_repository = GuildRepository()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        user_id = str(message.author.id)
        guild_id = str(message.guild.id)

        if self.channel_repository.is_ignored(str(message.channel.id), guild_id):
            return

        if self.cooldown_service.is_on_cooldown(user_id, guild_id):
            return

        self.cooldown_service.register(user_id, guild_id)

        xp_to_grant = self.experience_service.random_message_xp()
        result = self.experience_service.grant_xp(user_id, guild_id, xp_to_grant)

        if result.leveled_up:
            await self._send_levelup_message(message.channel, message.author, result.record.level, guild_id)

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
    await bot.add_cog(Leveling(bot))
