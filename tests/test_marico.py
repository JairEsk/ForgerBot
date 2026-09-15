import unittest
from unittest.mock import AsyncMock, MagicMock
from discord.ext import commands

from src.bot import COGS
from src.cogs.marico import Marico, setup


class MaricoCogTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.bot = MagicMock(spec=commands.Bot)
        self.cog = Marico(self.bot)

    async def test_marico_command_sends_diego(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.send = AsyncMock()

        await self.cog.marico.callback(self.cog, context)

        context.send.assert_awaited_once_with("diego")

    def test_marico_command_metadata_and_aliases(self) -> None:
        self.assertEqual(self.cog.marico.name, "marico")
        self.assertIn("Marico", self.cog.marico.aliases)

    async def test_setup_adds_marico_cog_to_bot(self) -> None:
        bot = MagicMock(spec=commands.Bot)
        bot.add_cog = AsyncMock()

        await setup(bot)

        bot.add_cog.assert_awaited_once()
        added_cog = bot.add_cog.call_args[0][0]
        self.assertIsInstance(added_cog, Marico)
        self.assertIs(added_cog.bot, bot)

    def test_marico_extension_is_registered_in_cogs_list(self) -> None:
        self.assertIn("src.cogs.marico", COGS)


if __name__ == "__main__":
    unittest.main()
