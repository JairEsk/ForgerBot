import discord
from discord.ext import commands
from discord import app_commands
from src.database.user_repository import UserRepository
from src.database.voice_repository import VoiceRepository
from src.cogs.rank import format_voice_time


class Leaderboard(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_repository = UserRepository()
        self.voice_repository = VoiceRepository()

    @app_commands.command(name="leaderboard", description="Shows the top 10 members with the most XP.")
    @app_commands.choices(category=[
        app_commands.Choice(name="Text XP", value="text"),
        app_commands.Choice(name="Voice XP", value="voice"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, category: app_commands.Choice[str]) -> None:
        guild_id = str(interaction.guild_id)
        
        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} Leaderboard",
            color=discord.Color.gold()
        )

        if category.value == "text":
            top_users = self.user_repository.fetch_top_users(guild_id, limit=10)
            if not top_users:
                embed.description = "No one has earned text XP yet."
            else:
                description = ""
                for index, (user_id, record) in enumerate(top_users, start=1):
                    description += f"**{index}.** <@{user_id}> — **Lvl {record.level}** ({record.xp} XP)\n"
                embed.description = description
                embed.set_footer(text="Category: Text XP")

        elif category.value == "voice":
            top_users = self.voice_repository.fetch_top_users(guild_id, limit=10)
            if not top_users:
                embed.description = "No one has earned voice XP yet."
            else:
                description = ""
                for index, (user_id, record) in enumerate(top_users, start=1):
                    time_str = format_voice_time(record.total_minutes)
                    description += f"**{index}.** <@{user_id}> — **Lvl {record.level}** ({record.xp} XP) 🎙 {time_str}\n"
                embed.description = description
                embed.set_footer(text="Category: Voice XP")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Leaderboard(bot))
