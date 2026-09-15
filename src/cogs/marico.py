from discord.ext import commands


class Marico(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="marico", aliases=["Marico"])
    async def marico(self, context: commands.Context) -> None:
        """Respond with 'diego' when !marico is invoked."""
        await context.send("diego")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Marico(bot))
