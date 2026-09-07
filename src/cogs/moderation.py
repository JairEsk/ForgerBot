from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands


class Moderation(commands.Cog):
    """Moderation commands for managing server channels and messages."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="clear",
        aliases=["purge", "clean"],
        description="Delete a specified number of messages from the channel."
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.guild_only()
    @app_commands.describe(
        amount="The number of messages to delete (1-100).",
        member="Optional member whose messages to delete."
    )
    async def clear(
        self,
        ctx: commands.Context,
        amount: commands.Range[int, 1, 100],
        member: Optional[discord.Member] = None
    ) -> None:
        if ctx.interaction is not None:
            await ctx.defer(ephemeral=True)
        else:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass

        check = (lambda m: m.author.id == member.id) if member is not None else None

        deleted = await ctx.channel.purge(
            limit=amount,
            check=check,
            bulk=True,
            reason=f"Clear executed by {ctx.author} ({ctx.author.id})"
        )

        count = len(deleted)
        plural = "message" if count == 1 else "messages"

        if count == 0:
            if member is not None:
                content = f"ℹ️ No messages found from {member.mention} to delete."
            else:
                content = "ℹ️ No messages found to delete."
        else:
            if member is not None:
                content = f"🗑️ Successfully deleted **{count}** {plural} from {member.mention}."
            else:
                content = f"🗑️ Successfully deleted **{count}** {plural}."

        try:
            if ctx.interaction is not None:
                await ctx.send(content, ephemeral=True)
            else:
                await ctx.send(content, delete_after=5)
        except discord.HTTPException:
            pass

    @clear.error
    async def clear_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.HybridCommandError):
            error = error.original

        if isinstance(error, (commands.MissingPermissions, app_commands.MissingPermissions)):
            msg = "❌ You need **Manage Messages** permissions to use this command."
        elif isinstance(error, (commands.BotMissingPermissions, app_commands.BotMissingPermissions)):
            msg = "❌ I need **Manage Messages** and **Read Message History** permissions to delete messages."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = (
                "⚠️ Please specify the number of messages to delete (1-100).\n"
                "**Usage:** `!clear <amount> [member]`\n"
                "**Example:** `!clear 10`"
            )
        elif isinstance(error, (commands.RangeError, app_commands.RangeError)):
            msg = "⚠️ The number of messages to delete must be between 1 and 100."
        elif isinstance(error, commands.MemberNotFound):
            msg = "⚠️ Member not found. Please mention a valid member or provide their ID."
        elif isinstance(error, (commands.BadArgument, commands.BadLiteralArgument)):
            msg = (
                "⚠️ Invalid argument. Please provide a valid number between 1 and 100.\n"
                "**Example:** `!clear 10`"
            )
        elif isinstance(error, (commands.NoPrivateMessage, app_commands.NoPrivateMessage)):
            msg = "❌ This command can only be used in a server channel."
        elif isinstance(error, discord.Forbidden):
            msg = "❌ I do not have permission to delete messages in this channel."
        else:
            msg = f"❌ An unexpected error occurred: {error}"

        try:
            if ctx.interaction is not None:
                if ctx.interaction.response.is_done():
                    await ctx.send(msg, ephemeral=True)
                else:
                    await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg, delete_after=5)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
