import discord
from discord.ext import commands
from discord import app_commands
from src.database.user_repository import UserRepository
from src.services.voice_service import VoiceService
from src.cogs.rank import format_voice_time


class Leaderboard(commands.Cog):

    def __init__(self, bot: commands.Bot, voice_service: VoiceService):
        self.bot = bot
        self.user_repository = UserRepository()
        self.voice_service = voice_service

    @app_commands.command(name="leaderboard", description="Shows the server leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        guild_id = str(interaction.guild_id)

        embed = discord.Embed(
            title="🏆 Guild Leaderboard",
            color=discord.Color.gold()
        )

        # Text leaderboard
        top_text = self.user_repository.fetch_top_users(guild_id, limit=10)
        if top_text:
            text_lines = ""
            for i, (user_id, record) in enumerate(top_text, start=1):
                text_lines += f"**#{i}** <@{user_id}> XP: **{record.xp}**\n"
        else:
            text_lines = "No data yet."
        embed.add_field(name="TOP 10 MESSAGES 💬", value=text_lines, inline=True)

        # Voice leaderboard
        top_voice = self.voice_service.fetch_top_records(guild_id, limit=10)
        if top_voice:
            voice_lines = ""
            for i, (user_id, record) in enumerate(top_voice, start=1):
                time_str = format_voice_time(record.total_minutes)
                voice_lines += f"**#{i}** <@{user_id}> 🕐 **{time_str}**\n"
        else:
            voice_lines = "No data yet."
        embed.add_field(name="TOP 10 VOICE 🔊", value=voice_lines, inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot, bot.voice_service))
