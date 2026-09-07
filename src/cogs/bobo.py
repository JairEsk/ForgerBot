from discord.ext import commands


class Bobo(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bobo", aliases=["Bobo"])
    async def bobo(self, context: commands.Context) -> None:
        """Respond with 'Diego' when !bobo is invoked."""
        await context.send("Diego")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bobo(bot))
