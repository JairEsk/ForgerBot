import discord
from discord.ext import commands
from discord import app_commands
from src.database.guild_repository import GuildRepository
from src.database.channel_repository import ChannelRepository
from src.services.cooldown_service import MINIMUM_COOLDOWN_SECONDS, MAXIMUM_COOLDOWN_SECONDS


class CooldownModal(discord.ui.Modal, title="Edit Cooldown"):
    cooldown_input = discord.ui.TextInput(
        label="Cooldown (seconds)",
        placeholder="e.g. 60",
        min_length=1,
        max_length=4
    )

    def __init__(self, guild_repository: GuildRepository):
        super().__init__()
        self.guild_repository = guild_repository

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not self.cooldown_input.value.isdigit():
            await interaction.response.send_message("Please enter a valid number.", ephemeral=True)
            return

        cooldown_value = int(self.cooldown_input.value)
        if not (MINIMUM_COOLDOWN_SECONDS <= cooldown_value <= MAXIMUM_COOLDOWN_SECONDS):
            await interaction.response.send_message(
                f"Cooldown must be between {MINIMUM_COOLDOWN_SECONDS} and {MAXIMUM_COOLDOWN_SECONDS} seconds.",
                ephemeral=True
            )
            return

        self.guild_repository.save_cooldown(str(interaction.guild_id), cooldown_value)
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=MainView(interaction.guild, self.guild_repository))


class LevelupMessageModal(discord.ui.Modal, title="Edit Level-up Message"):
    message_input = discord.ui.TextInput(
        label="Message",
        placeholder="🎉 {user} just reached level **{level}**!",
        style=discord.TextStyle.paragraph,
        max_length=200
    )

    def __init__(self, guild_repository: GuildRepository):
        super().__init__()
        self.guild_repository = guild_repository

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.guild_repository.save_levelup_message(str(interaction.guild_id), self.message_input.value)
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=MainView(interaction.guild, self.guild_repository))


class TextChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild: discord.Guild, channel_repository: ChannelRepository, guild_repository: GuildRepository):
        self.channel_repository = channel_repository
        self.guild_repository = guild_repository
        self.old_ignored_text = set()
        
        ignored = channel_repository.fetch_all(str(guild.id))
        defaults = []
        for cid in ignored:
            channel = guild.get_channel(int(cid))
            if channel and channel.type == discord.ChannelType.text:
                self.old_ignored_text.add(str(cid))
                defaults.append(discord.SelectDefaultValue(id=int(cid), type=discord.SelectDefaultValueType.channel))
                if len(defaults) == 25:
                    break

        super().__init__(
            placeholder="Select text channels to ignore...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25,
            default_values=defaults
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild_id = str(interaction.guild_id)
        new_ignored_text = {str(c.id) for c in self.values}
        
        for cid in self.old_ignored_text - new_ignored_text:
            self.channel_repository.remove(cid, guild_id)
            
        for cid in new_ignored_text - self.old_ignored_text:
            self.channel_repository.add(cid, guild_id)

        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=TextChannelsView(interaction.guild, self.channel_repository, self.guild_repository))


class VoiceChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild: discord.Guild, channel_repository: ChannelRepository, guild_repository: GuildRepository):
        self.channel_repository = channel_repository
        self.guild_repository = guild_repository
        self.old_ignored_voice = set()
        
        ignored = channel_repository.fetch_all(str(guild.id))
        defaults = []
        for cid in ignored:
            channel = guild.get_channel(int(cid))
            if channel and channel.type == discord.ChannelType.voice:
                self.old_ignored_voice.add(str(cid))
                defaults.append(discord.SelectDefaultValue(id=int(cid), type=discord.SelectDefaultValueType.channel))
                if len(defaults) == 25:
                    break

        super().__init__(
            placeholder="Select voice channels to ignore...",
            channel_types=[discord.ChannelType.voice],
            min_values=0,
            max_values=25,
            default_values=defaults
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild_id = str(interaction.guild_id)
        new_ignored_voice = {str(c.id) for c in self.values}
        
        for cid in self.old_ignored_voice - new_ignored_voice:
            self.channel_repository.remove(cid, guild_id)
            
        for cid in new_ignored_voice - self.old_ignored_voice:
            self.channel_repository.add(cid, guild_id)

        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=VoiceChannelsView(interaction.guild, self.channel_repository, self.guild_repository))


class TextChannelsView(discord.ui.View):
    def __init__(self, guild: discord.Guild, channel_repository: ChannelRepository, guild_repository: GuildRepository):
        super().__init__(timeout=120)
        self.guild_repository = guild_repository
        self.add_item(TextChannelSelect(guild, channel_repository, guild_repository))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=MainView(interaction.guild, self.guild_repository))


class VoiceChannelsView(discord.ui.View):
    def __init__(self, guild: discord.Guild, channel_repository: ChannelRepository, guild_repository: GuildRepository):
        super().__init__(timeout=120)
        self.guild_repository = guild_repository
        self.add_item(VoiceChannelSelect(guild, channel_repository, guild_repository))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=MainView(interaction.guild, self.guild_repository))


class LevelUpChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository):
        self.guild_repository = guild_repository
        settings = guild_repository.fetch_settings(str(guild.id))
        
        defaults = []
        if settings.levelup_channel_id:
            channel = guild.get_channel(int(settings.levelup_channel_id))
            if channel and channel.type == discord.ChannelType.text:
                defaults.append(discord.SelectDefaultValue(id=int(channel.id), type=discord.SelectDefaultValueType.channel))

        super().__init__(
            placeholder="Select level-up announcement channel...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=1,
            default_values=defaults
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if len(self.values) == 0:
            self.guild_repository.save_levelup_channel(str(interaction.guild_id), None)
        else:
            self.guild_repository.save_levelup_channel(str(interaction.guild_id), str(self.values[0].id))
            
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=LevelUpChannelView(interaction.guild, self.guild_repository))


class LevelUpChannelView(discord.ui.View):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository):
        super().__init__(timeout=120)
        self.guild_repository = guild_repository
        self.add_item(LevelUpChannelSelect(guild, guild_repository))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=MainView(interaction.guild, self.guild_repository))


class MainView(discord.ui.View):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository, channel_repository: ChannelRepository = None):
        super().__init__(timeout=120)
        self.guild_repository = guild_repository
        self.channel_repository = channel_repository or ChannelRepository()

    @discord.ui.button(label="📢 Level-up Channel", style=discord.ButtonStyle.primary)
    async def levelup_channel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(view=LevelUpChannelView(interaction.guild, self.guild_repository))

    @discord.ui.button(label="💬 Text Channels", style=discord.ButtonStyle.primary, row=0)
    async def text_channels(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(
            view=TextChannelsView(interaction.guild, self.channel_repository, self.guild_repository)
        )

    @discord.ui.button(label="🎙️ Voice Channels", style=discord.ButtonStyle.primary, row=0)
    async def voice_channels(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(
            view=VoiceChannelsView(interaction.guild, self.channel_repository, self.guild_repository)
        )

    @discord.ui.button(label="⏱ Cooldown", style=discord.ButtonStyle.secondary, row=1)
    async def cooldown(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(CooldownModal(self.guild_repository))

    @discord.ui.button(label="📢 Message", style=discord.ButtonStyle.secondary, row=1)
    async def message(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(LevelupMessageModal(self.guild_repository))

    @discord.ui.button(label="✖ Close", style=discord.ButtonStyle.danger, row=2)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()


def build_settings_embed(guild: discord.Guild, guild_repository: GuildRepository) -> discord.Embed:
    settings = guild_repository.fetch_settings(str(guild.id))
    ignored_channels = ChannelRepository().fetch_all(str(guild.id))

    ignored_channels_display = (
        ", ".join([f"<#{channel_id}>" for channel_id in ignored_channels])
        if ignored_channels else "None"
    )

    levelup_channel_display = (
        f"<#{settings.levelup_channel_id}>"
        if settings.levelup_channel_id else "Same channel as message"
    )

    embed = discord.Embed(
        title="⚙️ ForgerBot — Level System Configuration",
        color=discord.Color.blurple()
    )
    embed.add_field(name="⏱ Cooldown",           value=f"`{settings.cooldown}s`", inline=True)
    embed.add_field(name="📢 Level-up Channel",   value=levelup_channel_display, inline=True)
    embed.add_field(name="🔇 Ignored Channels",   value=ignored_channels_display, inline=False)
    embed.add_field(name="📢 Level-up Message",   value=f"`{settings.levelup_message}`", inline=False)
    embed.set_footer(text=f"Server: {guild.name}")

    return embed


class Settings(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_repository = GuildRepository()
        self.channel_repository = ChannelRepository()

    @app_commands.command(name="configure", description="Open the ForgerBot configuration panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def configure(self, interaction: discord.Interaction) -> None:
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.send_message(
            embed=embed,
            view=MainView(interaction.guild, self.guild_repository, self.channel_repository),
            ephemeral=True
        )

    @configure.error
    async def configure_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need **Administrator** permissions to use this command.",
                ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Settings(bot))
