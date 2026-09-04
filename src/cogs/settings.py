import discord
from discord.ext import commands
from discord import app_commands
from src.database.guild_repository import (
    GuildRepository,
    LEVELUP_MODE_CURRENT,
    LEVELUP_MODE_CUSTOM,
    LEVELUP_MODE_DISABLED,
    LEVELUP_MODE_DM,
)
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
        self.previous_ignored_text_channel_ids = set()
        
        all_ignored_channel_ids = channel_repository.fetch_all(str(guild.id))
        
        for channel_id_string in all_ignored_channel_ids:
            channel_instance = guild.get_channel(int(channel_id_string))
            
            # Guard clause to ignore deleted channels or voice channels
            if not channel_instance or channel_instance.type != discord.ChannelType.text:
                continue
                
            self.previous_ignored_text_channel_ids.add(channel_id_string)

        super().__init__(
            placeholder="Select text channels to ignore...",
            channel_types=[discord.ChannelType.text],
            min_values=0,
            max_values=25
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild_id_string = str(interaction.guild_id)
        
        # 1. Remove all old ignored text channels (overwrite mechanism)
        for old_channel_id in self.previous_ignored_text_channel_ids:
            self.channel_repository.remove(old_channel_id, guild_id_string)
            
        # 2. Add the newly selected text channels
        for selected_channel in self.values:
            self.channel_repository.add(str(selected_channel.id), guild_id_string)

        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=TextChannelsView(interaction.guild, self.channel_repository, self.guild_repository))


class VoiceChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild: discord.Guild, channel_repository: ChannelRepository, guild_repository: GuildRepository):
        self.channel_repository = channel_repository
        self.guild_repository = guild_repository
        self.previous_ignored_voice_channel_ids = set()
        
        all_ignored_channel_ids = channel_repository.fetch_all(str(guild.id))
        
        for channel_id_string in all_ignored_channel_ids:
            channel_instance = guild.get_channel(int(channel_id_string))
            
            # Guard clause to ignore deleted channels or text channels
            if not channel_instance or channel_instance.type != discord.ChannelType.voice:
                continue
                
            self.previous_ignored_voice_channel_ids.add(channel_id_string)

        super().__init__(
            placeholder="Select voice channels to ignore...",
            channel_types=[discord.ChannelType.voice],
            min_values=0,
            max_values=25
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        guild_id_string = str(interaction.guild_id)
        
        # 1. Remove all old ignored voice channels
        for old_channel_id in self.previous_ignored_voice_channel_ids:
            self.channel_repository.remove(old_channel_id, guild_id_string)
            
        # 2. Add the newly selected voice channels
        for selected_channel in self.values:
            self.channel_repository.add(str(selected_channel.id), guild_id_string)

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


class LevelUpModeSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository):
        self.guild_repository = guild_repository
        current_mode = guild_repository.fetch_settings(str(guild.id)).levelup_mode

        super().__init__(
            placeholder="Select where level-ups are announced...",
            options=[
                discord.SelectOption(
                    label="Current channel",
                    value=LEVELUP_MODE_CURRENT,
                    description="Announce where the member leveled up.",
                    emoji="💬",
                    default=current_mode == LEVELUP_MODE_CURRENT
                ),
                discord.SelectOption(
                    label="Custom channel",
                    value=LEVELUP_MODE_CUSTOM,
                    description="Always announce in one specific channel.",
                    emoji="📢",
                    default=current_mode == LEVELUP_MODE_CUSTOM
                ),
                discord.SelectOption(
                    label="Direct message",
                    value=LEVELUP_MODE_DM,
                    description="DM the member who leveled up.",
                    emoji="✉️",
                    default=current_mode == LEVELUP_MODE_DM
                ),
                discord.SelectOption(
                    label="Disabled",
                    value=LEVELUP_MODE_DISABLED,
                    description="Never announce level-ups.",
                    emoji="🚫",
                    default=current_mode == LEVELUP_MODE_DISABLED
                ),
            ],
            row=0
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        selected_mode = self.values[0]
        settings = self.guild_repository.fetch_settings(str(interaction.guild_id))

        if selected_mode == LEVELUP_MODE_CUSTOM and settings.levelup_channel_id is None:
            await interaction.response.send_message(
                "Pick a channel in the dropdown below first — custom mode needs one.",
                ephemeral=True
            )
            return

        self.guild_repository.save_levelup_mode(str(interaction.guild_id), selected_mode)

        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=LevelUpChannelView(interaction.guild, self.guild_repository))


class LevelUpChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository):
        self.guild_repository = guild_repository
        settings = guild_repository.fetch_settings(str(guild.id))

        # Show the saved channel as pre-selected so the panel reflects stored config.
        default_values = []
        if settings.levelup_channel_id is not None:
            default_values = [
                discord.SelectDefaultValue(
                    id=int(settings.levelup_channel_id),
                    type=discord.SelectDefaultValueType.channel
                )
            ]

        super().__init__(
            placeholder="Select level-up announcement channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            default_values=default_values,
            row=1
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.guild_repository.save_levelup_channel(str(interaction.guild_id), str(self.values[0].id))

        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=LevelUpChannelView(interaction.guild, self.guild_repository))


class LevelUpChannelView(discord.ui.View):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository):
        super().__init__(timeout=120)
        self.guild_repository = guild_repository
        self.add_item(LevelUpModeSelect(guild, guild_repository))
        self.add_item(LevelUpChannelSelect(guild, guild_repository))

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(embed=embed, view=MainView(interaction.guild, self.guild_repository))


class MainView(discord.ui.View):
    def __init__(self, guild: discord.Guild, guild_repository: GuildRepository, channel_repository: ChannelRepository = None):
        super().__init__(timeout=120)
        self.guild_repository = guild_repository
        self.channel_repository = channel_repository or ChannelRepository()

        settings = self.guild_repository.fetch_settings(str(guild.id))
        if settings.auto_ignore_afk:
            self.toggle_afk_button.label = "💤 AFK: Auto (ON)"
            self.toggle_afk_button.style = discord.ButtonStyle.success
        else:
            self.toggle_afk_button.label = "💤 AFK: Auto (OFF)"
            self.toggle_afk_button.style = discord.ButtonStyle.secondary

    @discord.ui.button(label="📢 Level-up Channel", style=discord.ButtonStyle.primary, row=0)
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

    @discord.ui.button(label="💤 AFK: Auto", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_afk_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        settings = self.guild_repository.fetch_settings(str(interaction.guild_id))
        new_state = not settings.auto_ignore_afk
        self.guild_repository.save_auto_ignore_afk(str(interaction.guild_id), new_state)

        # Synchronize active sessions if an AFK channel exists
        if interaction.guild and interaction.guild.afk_channel:
            voice_service = getattr(interaction.client, "voice_service", None)
            if voice_service:
                guild_id_str = str(interaction.guild_id)
                for member in interaction.guild.afk_channel.members:
                    if member.bot:
                        continue
                    user_id_str = str(member.id)
                    if new_state:
                        # Auto-exclusion enabled: end any session in AFK channel
                        voice_service.end_session(user_id_str, guild_id_str)
                    else:
                        # Auto-exclusion disabled: start session if channel not manually ignored
                        if not self.channel_repository.is_ignored(str(interaction.guild.afk_channel.id), guild_id_str):
                            voice_service.start_session(user_id_str, guild_id_str)

        embed = build_settings_embed(interaction.guild, self.guild_repository)
        await interaction.response.edit_message(
            embed=embed,
            view=MainView(interaction.guild, self.guild_repository, self.channel_repository)
        )

    @discord.ui.button(label="✖ Close", style=discord.ButtonStyle.danger, row=2)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()


def build_settings_embed(guild: discord.Guild, guild_repository: GuildRepository) -> discord.Embed:
    settings = guild_repository.fetch_settings(str(guild.id))
    channel_repository = ChannelRepository()
    
    all_ignored_channels = channel_repository.fetch_all(str(guild.id))
    valid_ignored_channels = []

    # Clean up ghost channels that no longer exist in the guild
    for channel_id_string in all_ignored_channels:
        channel_instance = guild.get_channel(int(channel_id_string))
        
        # Guard clause: if channel is deleted, clean it from DB and don't display
        if not channel_instance:
            channel_repository.remove(channel_id_string, str(guild.id))
            continue
            
        valid_ignored_channels.append(channel_id_string)

    ignored_channels_display = (
        ", ".join([f"<#{channel_id_string}>" for channel_id_string in valid_ignored_channels])
        if valid_ignored_channels else "None"
    )

    if settings.levelup_mode == LEVELUP_MODE_CUSTOM:
        levelup_channel_display = f"<#{settings.levelup_channel_id}>"
    elif settings.levelup_mode == LEVELUP_MODE_DM:
        levelup_channel_display = "✉️ Direct message"
    elif settings.levelup_mode == LEVELUP_MODE_DISABLED:
        levelup_channel_display = "🚫 Disabled"
    else:
        levelup_channel_display = "💬 Same channel as message"

    if settings.auto_ignore_afk:
        if guild.afk_channel:
            afk_display = f"✅ Enabled (<#{guild.afk_channel.id}>)"
        else:
            afk_display = "✅ Enabled *(no AFK channel set)*"
    else:
        afk_display = "❌ Disabled"

    embed = discord.Embed(
        title="⚙️ ForgerBot — Level System Configuration",
        color=discord.Color.blurple()
    )
    embed.add_field(name="⏱ Cooldown",           value=f"`{settings.cooldown}s`", inline=True)
    embed.add_field(name="📢 Level-up Channel",   value=levelup_channel_display, inline=True)
    embed.add_field(name="💤 Auto-Exclude AFK",   value=afk_display, inline=True)
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
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

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
