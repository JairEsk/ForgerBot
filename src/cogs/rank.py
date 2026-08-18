import discord
from discord.ext import commands
from discord import app_commands
from src.database.user_repository import UserRepository
from src.services.voice_service import VoiceService
from src.services.experience_service import ExperienceService


def format_voice_time(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


class Rank(commands.Cog):

    def __init__(self, bot: commands.Bot, voice_service: VoiceService):
        self.bot = bot
        self.user_repository = UserRepository()
        self.voice_service = voice_service
        self.experience_service = ExperienceService()

    @app_commands.command(name="rank", description="Check your current level, XP and voice stats.")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        target_member = member or interaction.user
        user_id = str(target_member.id)
        guild_id = str(interaction.guild_id)

        text_record = self.user_repository.fetch(user_id, guild_id)
        voice_record = self.voice_service.fetch_record(user_id, guild_id)

        text_xp_required = self.experience_service.calculate_xp_required(text_record.level + 1)

        embed = discord.Embed(
            title=f"{target_member.display_name}'s Stats",
            color=discord.Color.blue()
        )

        embed.add_field(name="💬 Text Level", value=str(text_record.level), inline=True)
        embed.add_field(name="💬 Text XP",   value=f"{text_record.xp} / {text_xp_required}", inline=True)
        embed.add_field(name="\u200b",        value="\u200b", inline=True)

        embed.add_field(name="🕐 Voice Time",  value=format_voice_time(voice_record.total_minutes), inline=False)

        embed.set_thumbnail(url=target_member.display_avatar.url)

        await interaction.response.send_message(embed=embed)

