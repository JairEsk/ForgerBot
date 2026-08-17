import discord
from discord.ext import commands
from src.config import PREFIX

from src.services.voice_service import VoiceService

COGS = [
    "src.cogs.leveling",
    "src.cogs.settings",
    "src.cogs.leaderboard",
]

class ForgerBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True

        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None
        )
        self.voice_service = VoiceService()

    async def setup_hook(self) -> None:
        for cog in COGS:
            await self.load_extension(cog)

        from src.cogs.voice import Voice
        from src.cogs.rank import Rank
        
        await self.add_cog(Voice(self, self.voice_service))
        await self.add_cog(Rank(self, self.voice_service))

        await self.tree.sync()

    async def on_ready(self) -> None:
        print(f"Bot online as {self.user.name}")
        print(f"Slash commands synced — {len(self.tree.get_commands())} commands registered")
