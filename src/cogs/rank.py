import discord
from discord.ext import commands
from discord import app_commands
from src.database.user_repository import UserRepository
from src.database.voice_repository import VoiceRepository
from src.services.experience_service import ExperienceService


def format_voice_time(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class Rank(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_repository = UserRepository()
        self.voice_repository = VoiceRepository()
        self.experience_service = ExperienceService()

    @app_commands.command(name="rank", description="Check your current level, XP and voice time.")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        target_member = member or interaction.user
        user_id = str(target_member.id)
        guild_id = str(interaction.guild_id)

        user_record = self.user_repository.fetch(user_id, guild_id)
        voice_record = self.voice_repository.fetch(user_id, guild_id)
        xp_required = self.experience_service.calculate_xp_required(user_record.level + 1)

        embed = discord.Embed(
            title=f"{target_member.display_name}'s Stats",
            color=discord.Color.blue()
        )
        embed.add_field(name="Level", value=str(user_record.level), inline=True)
        embed.add_field(name="XP", value=f"{user_record.xp} / {xp_required}", inline=True)
        embed.add_field(name="🎙 Voice Time", value=format_voice_time(voice_record.total_minutes), inline=True)
        embed.set_thumbnail(url=target_member.display_avatar.url)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Rank(bot))
