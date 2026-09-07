import unittest
from unittest.mock import AsyncMock, MagicMock
from discord.ext import commands

from src.bot import COGS
from src.cogs.bobo import Bobo, setup


class BoboCogTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.bot = MagicMock(spec=commands.Bot)
        self.cog = Bobo(self.bot)

    async def test_bobo_command_sends_diego(self) -> None:
        context = MagicMock(spec=commands.Context)
        context.send = AsyncMock()

        await self.cog.bobo.callback(self.cog, context)

        context.send.assert_awaited_once_with("Diego")

    def test_bobo_command_metadata_and_aliases(self) -> None:
        self.assertEqual(self.cog.bobo.name, "bobo")
        self.assertIn("Bobo", self.cog.bobo.aliases)

    async def test_setup_adds_bobo_cog_to_bot(self) -> None:
        bot = MagicMock(spec=commands.Bot)
        bot.add_cog = AsyncMock()

        await setup(bot)

        bot.add_cog.assert_awaited_once()
        added_cog = bot.add_cog.call_args[0][0]
        self.assertIsInstance(added_cog, Bobo)
        self.assertIs(added_cog.bot, bot)

    def test_bobo_extension_is_registered_in_cogs_list(self) -> None:
        self.assertIn("src.cogs.bobo", COGS)


if __name__ == "__main__":
    unittest.main()
