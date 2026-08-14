import discord
from discord.ext import commands
from src.services.experience_service import ExperienceService
from src.services.cooldown_service import CooldownService
from src.services.levelup_service import LevelUpService
from src.database.user_repository import UserRepository, TextExperienceRecord
from src.database.channel_repository import ChannelRepository


class Leveling(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_repository = UserRepository()
        self.experience_service = ExperienceService()
        self.cooldown_service = CooldownService()
        self.channel_repository = ChannelRepository()
        self.levelup_service = LevelUpService()

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

        current_record = self.user_repository.fetch(user_id, guild_id)
        xp_to_grant = self.experience_service.random_message_xp()
        result = self.experience_service.compute_grant(current_record.xp, current_record.level, xp_to_grant)

        self.user_repository.save(user_id, guild_id, TextExperienceRecord(xp=result.xp, level=result.level))

        if result.leveled_up:
            await self.levelup_service.announce_text_levelup(message, result.level)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leveling(bot))
