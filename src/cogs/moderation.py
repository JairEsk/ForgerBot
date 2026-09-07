import discord
from discord.ext import commands

MAXIMUM_CLEAR_AMOUNT = 100
CONFIRMATION_DELETE_AFTER_SECONDS = 5.0


class Moderation(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="clear", aliases=["purge", "clean"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def clear(self, context: commands.Context, amount: int) -> None:
        """Delete the last `amount` messages from the current channel."""
        if not (1 <= amount <= MAXIMUM_CLEAR_AMOUNT):
            await self._send_feedback(
                context,
                f"Amount must be between 1 and {MAXIMUM_CLEAR_AMOUNT}."
            )
            return

        # The invoking message counts as one deletion so the user sees `amount` removed.
        deleted_messages = await context.channel.purge(
            limit=amount + 1,
            reason=f"Clear command invoked by {context.author} (ID: {context.author.id})"
        )
        was_invoker_deleted = any(msg.id == context.message.id for msg in deleted_messages)
        deleted_count = len(deleted_messages) - (1 if was_invoker_deleted else 0)

        await context.channel.send(
            f"Deleted {deleted_count} message(s).",
            delete_after=CONFIRMATION_DELETE_AFTER_SECONDS
        )

    async def _send_feedback(self, context: commands.Context, message: str) -> None:
        try:
            await context.reply(message, delete_after=CONFIRMATION_DELETE_AFTER_SECONDS)
        except (discord.NotFound, discord.HTTPException):
            await context.send(message, delete_after=CONFIRMATION_DELETE_AFTER_SECONDS)

    @clear.error
    async def clear_error(self, context: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            message = "Usage: `!clear <amount>`"
        elif isinstance(error, commands.BadArgument):
            message = "Amount must be a whole number."
        elif isinstance(error, commands.MissingPermissions):
            message = "You need the **Manage Messages** permission to use this command."
        elif isinstance(error, commands.BotMissingPermissions):
            message = "I need **Manage Messages** and **Read Message History** permissions here."
        elif isinstance(error, commands.NoPrivateMessage):
            message = "This command can only be used in a server."
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            message = "I am not allowed to delete messages in this channel."
        else:
            raise error

        await self._send_feedback(context, message)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
