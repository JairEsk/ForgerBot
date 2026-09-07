import unittest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

from src.cogs.moderation import Moderation, MAXIMUM_CLEAR_AMOUNT


class ModerationCogTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.bot = MagicMock(spec=commands.Bot)
        self.cog = Moderation(self.bot)

    async def test_clear_purges_amount_plus_invoker_and_reports_count(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.channel = MagicMock()
        context.author = MagicMock()
        context.author.__str__.return_value = "Moderator#0001"
        context.author.id = 999
        invoking_message = MagicMock(spec=discord.Message)
        invoking_message.id = 123
        context.message = invoking_message

        other_msg1 = MagicMock(spec=discord.Message)
        other_msg1.id = 100
        other_msg2 = MagicMock(spec=discord.Message)
        other_msg2.id = 101

        context.channel.purge = AsyncMock(return_value=[invoking_message, other_msg1, other_msg2])
        context.channel.send = AsyncMock()

        await self.cog.clear.callback(self.cog, context, amount=2)

        context.channel.purge.assert_awaited_once_with(
            limit=3,
            reason="Clear command invoked by Moderator#0001 (ID: 999)"
        )
        context.channel.send.assert_awaited_once_with(
            "Deleted 2 message(s).",
            delete_after=5.0
        )

    async def test_clear_without_invoking_message_in_purge_counts_all(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.channel = MagicMock()
        context.author = MagicMock()
        context.author.__str__.return_value = "Moderator#0001"
        context.author.id = 999
        invoking_message = MagicMock(spec=discord.Message)
        invoking_message.id = 123
        context.message = invoking_message

        other_msg1 = MagicMock(spec=discord.Message)
        other_msg1.id = 100
        other_msg2 = MagicMock(spec=discord.Message)
        other_msg2.id = 101

        context.channel.purge = AsyncMock(return_value=[other_msg1, other_msg2])
        context.channel.send = AsyncMock()

        await self.cog.clear.callback(self.cog, context, amount=2)

        context.channel.purge.assert_awaited_once_with(
            limit=3,
            reason="Clear command invoked by Moderator#0001 (ID: 999)"
        )
        context.channel.send.assert_awaited_once_with(
            "Deleted 2 message(s).",
            delete_after=5.0
        )

    async def test_clear_rejects_amount_below_minimum(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()
        context.channel = MagicMock()
        context.channel.purge = AsyncMock()

        await self.cog.clear.callback(self.cog, context, amount=0)

        context.channel.purge.assert_not_called()
        context.reply.assert_awaited_once()
        self.assertIn("Amount must be between 1 and 100", context.reply.call_args[0][0])

    async def test_clear_rejects_amount_above_maximum(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()
        context.channel = MagicMock()
        context.channel.purge = AsyncMock()

        await self.cog.clear.callback(self.cog, context, amount=MAXIMUM_CLEAR_AMOUNT + 1)

        context.channel.purge.assert_not_called()
        context.reply.assert_awaited_once()
        self.assertIn("Amount must be between 1 and 100", context.reply.call_args[0][0])

    async def test_clear_error_missing_required_argument(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()

        param = MagicMock()
        param.name = "amount"
        error = commands.MissingRequiredArgument(param)

        await self.cog.clear_error(context, error)

        context.reply.assert_awaited_once()
        self.assertIn("Usage: `!clear <amount>`", context.reply.call_args[0][0])

    async def test_clear_error_bad_argument(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()

        error = commands.BadArgument()

        await self.cog.clear_error(context, error)

        context.reply.assert_awaited_once()
        self.assertIn("Amount must be a whole number", context.reply.call_args[0][0])

    async def test_clear_error_missing_permissions(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()

        error = commands.MissingPermissions(["manage_messages"])

        await self.cog.clear_error(context, error)

        context.reply.assert_awaited_once()
        self.assertIn("Manage Messages", context.reply.call_args[0][0])

    async def test_clear_error_bot_missing_permissions(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()

        error = commands.BotMissingPermissions(["manage_messages", "read_message_history"])

        await self.cog.clear_error(context, error)

        context.reply.assert_awaited_once()
        self.assertIn("Manage Messages", context.reply.call_args[0][0])
        self.assertIn("Read Message History", context.reply.call_args[0][0])

    async def test_clear_error_no_private_message(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.reply = AsyncMock()

        error = commands.NoPrivateMessage()

        await self.cog.clear_error(context, error)

        context.reply.assert_awaited_once()
        self.assertIn("server", context.reply.call_args[0][0])

    async def test_send_feedback_falls_back_to_send_when_reply_fails(self) -> None:
        context = MagicMock(spec=commands.Context)
        response = MagicMock()
        response.status = 404
        context.reply = AsyncMock(side_effect=discord.NotFound(response, "Unknown Message"))
        context.send = AsyncMock()

        await self.cog._send_feedback(context, "Test error message")

        context.reply.assert_awaited_once()
        context.send.assert_awaited_once_with("Test error message", delete_after=5.0)


if __name__ == "__main__":
    unittest.main()
