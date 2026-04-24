import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, BaseLayoutView
from Modules.database import db


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = None
    
    def get_bot_id(self):
        if self.bot_id is None:
            self.bot_id = self.bot.user.id if self.bot.user else None
        return self.bot_id
    
    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        
        if interaction.user.id == interaction.guild.owner_id:
            return True
        
        settings = db.get_guild(interaction.guild.id)
        if settings.admin_role_id:
            member = interaction.guild.get_member(interaction.user.id)
            if member and settings.admin_role_id in [role.id for role in member.roles]:
                return True
        
        return False

    @app_commands.command(name="setup", description="Configure Niro for your server")
    @app_commands.describe(category="Which category to configure")
    @app_commands.choices(category=[
        app_commands.Choice(name="Moderation", value="moderation"),
        app_commands.Choice(name="Leveling", value="leveling"),
        app_commands.Choice(name="Giveaway", value="giveaway"),
        app_commands.Choice(name="Logging", value="logging"),
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="All Settings", value="all"),
    ])
    @app_commands.guild_only()
    async def setup_slash(self, interaction: discord.Interaction, category: str = "all"):
        if not await self.check_permissions(interaction):
            embed = EmbedComponent.error("Permission Denied", "Only the server owner or admin role can use this command.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if category == "all":
            await self.show_all_settings(interaction)
        elif category == "moderation":
            await self.show_moderation_settings(interaction)
        elif category == "leveling":
            await self.show_leveling_settings(interaction)
        elif category == "giveaway":
            await self.show_giveaway_settings(interaction)
        elif category == "logging":
            await self.show_logging_settings(interaction)
        elif category == "welcome":
            await self.show_welcome_settings(interaction)
    
    async def show_all_settings(self, interaction: discord.Interaction):
        guild_settings = db.get_guild(interaction.guild.id)
        
        view = SetupSelectView(self.bot, interaction.user.id, guild_settings)
        await interaction.response.send_message(view=view, ephemeral=True)
    
    async def show_moderation_settings(self, interaction: discord.Interaction):
        guild_settings = db.get_guild(interaction.guild.id)
        
        view = ModerationSetupView(self.bot, interaction.user.id, guild_settings)
        await interaction.response.send_message(view=view, ephemeral=True)
    
    async def show_leveling_settings(self, interaction: discord.Interaction):
        guild_settings = db.get_guild(interaction.guild.id)
        
        view = LevelingSetupView(self.bot, interaction.user.id, guild_settings)
        await interaction.response.send_message(view=view, ephemeral=True)
    
    async def show_giveaway_settings(self, interaction: discord.Interaction):
        guild_settings = db.get_guild(interaction.guild.id)
        
        view = GiveawaySetupView(self.bot, interaction.user.id, guild_settings)
        await interaction.response.send_message(view=view, ephemeral=True)
    
    async def show_logging_settings(self, interaction: discord.Interaction):
        guild_settings = db.get_guild(interaction.guild.id)
        
        view = LoggingSetupView(self.bot, interaction.user.id, guild_settings)
        await interaction.response.send_message(view=view, ephemeral=True)
    
    async def show_welcome_settings(self, interaction: discord.Interaction):
        guild_settings = db.get_guild(interaction.guild.id)
        
        view = WelcomeSetupView(self.bot, interaction.user.id, guild_settings)
        await interaction.response.send_message(view=view, ephemeral=True)


class SetupSelectView(BaseLayoutView):
    def __init__(self, bot, user_id: int, guild_settings):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings = guild_settings
        self._build_container()
    
    def _build_container(self):
        self.clear_items()
        self.btn_moderation = ui.Button(
            label="Moderation", style=discord.ButtonStyle.secondary, emoji="🛡️", custom_id="btn_moderation"
        )
        self.btn_moderation.callback = self._on_moderation
        
        self.btn_leveling = ui.Button(
            label="Leveling", style=discord.ButtonStyle.secondary, emoji="⭐", custom_id="btn_leveling"
        )
        self.btn_leveling.callback = self._on_leveling
        
        self.btn_giveaway = ui.Button(
            label="Giveaway", style=discord.ButtonStyle.secondary, emoji="🎁", custom_id="btn_giveaway"
        )
        self.btn_giveaway.callback = self._on_giveaway
        
        self.btn_logging = ui.Button(
            label="Logging", style=discord.ButtonStyle.secondary, emoji="📝", custom_id="btn_logging"
        )
        self.btn_logging.callback = self._on_logging
        
        self.btn_welcome = ui.Button(
            label="Welcome", style=discord.ButtonStyle.secondary, emoji="👋", custom_id="btn_welcome"
        )
        self.btn_welcome.callback = self._on_welcome
        
        mod_role = f"<@&{self.settings.mod_role_id}>" if self.settings.mod_role_id else "Not set"
        admin_role = f"<@&{self.settings.admin_role_id}>" if self.settings.admin_role_id else "Not set"
        gw_role = f"<@&{self.settings.giveaway_role_id}>" if self.settings.giveaway_role_id else "Not set"
        log_ch = f"<#{self.settings.log_channel_id}>" if self.settings.log_channel_id else "Not set"
        welc_ch = f"<#{self.settings.welcome_channel_id}>" if self.settings.welcome_channel_id else "Not set"
        
        desc = (
            "## ⚙️ Server Settings\nConfigure Niro for your server:\n\n"
            f"**🛡️ Moderator Role**: {mod_role}\n"
            f"**⚡ Admin Role**: {admin_role}\n"
            f"**🎁 Giveaway Role**: {gw_role}\n"
            f"**📝 Logging Channel**: {log_ch}\n"
            f"**👋 Welcome Channel**: {welc_ch}\n"
            f"**⭐ Leveling**: {'Enabled ✅' if self.settings.leveling_enabled else 'Disabled ❌'}\n"
            f"**💬 XP per message**: {self.settings.xp_per_message} XP\n"
            f"**⏱️ XP Cooldown**: {self.settings.xp_cooldown} seconds"
        )
        
        self.container = ui.Container(
            ui.TextDisplay(desc),
            ui.ActionRow(self.btn_moderation, self.btn_leveling, self.btn_giveaway),
            ui.ActionRow(self.btn_logging, self.btn_welcome),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return False
        return True
    
    async def _on_moderation(self, interaction: discord.Interaction):
        view = ModerationSetupView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_leveling(self, interaction: discord.Interaction):
        view = LevelingSetupView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_giveaway(self, interaction: discord.Interaction):
        view = GiveawaySetupView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_logging(self, interaction: discord.Interaction):
        view = LoggingSetupView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_welcome(self, interaction: discord.Interaction):
        view = WelcomeSetupView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)


class ModerationSetupView(ui.LayoutView):
    def __init__(self, bot, user_id: int, settings):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings = settings
        self._build_container()
    
    def _build_container(self):
        self.clear_items()
        self.sel_mod_role = ui.RoleSelect(
            placeholder="Select Mod Role...", min_values=1, max_values=1, custom_id="sel_mod_role"
        )
        self.sel_mod_role.callback = self._on_mod_role
        
        self.sel_admin_role = ui.RoleSelect(
            placeholder="Select Admin Role...", min_values=1, max_values=1, custom_id="sel_admin_role"
        )
        self.sel_admin_role.callback = self._on_admin_role
        
        self.btn_back = ui.Button(label="Back to Menu", style=discord.ButtonStyle.secondary, emoji="◀️", custom_id="btn_back")
        self.btn_back.callback = self._on_back
        
        mod_role_text = f"<@&{self.settings.mod_role_id}>" if self.settings.mod_role_id else "Not set"
        admin_role_text = f"<@&{self.settings.admin_role_id}>" if self.settings.admin_role_id else "Not set"
        
        self.container = ui.Container(
            ui.TextDisplay(f"## 🛡️ Moderation Settings\n\nConfigure moderation roles:\n\n**Mod Role**: {mod_role_text}\n**Admin Role**: {admin_role_text}"),
            ui.ActionRow(self.sel_mod_role),
            ui.ActionRow(self.sel_admin_role),
            ui.ActionRow(self.btn_back),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return False
        return True
    
    async def _on_back(self, interaction: discord.Interaction):
        view = SetupSelectView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_mod_role(self, interaction: discord.Interaction):
        if not self.sel_mod_role.values:
            return await interaction.response.defer()
            
        role_id = self.sel_mod_role.values[0].id
        db.update_guild(interaction.guild.id, mod_role_id=role_id)
        self.settings.mod_role_id = role_id
        self._build_container()
        await interaction.response.edit_message(view=self)
    
    async def _on_admin_role(self, interaction: discord.Interaction):
        if not self.sel_admin_role.values:
            return await interaction.response.defer()
            
        role_id = self.sel_admin_role.values[0].id
        db.update_guild(interaction.guild.id, admin_role_id=role_id)
        self.settings.admin_role_id = role_id
        self._build_container()
        await interaction.response.edit_message(view=self)


class LevelingXpModal(ui.Modal, title="Set XP per Message"):
    xp = ui.TextInput(label="XP Amount (1-100)", placeholder="e.g., 10", min_length=1, max_length=3)
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.xp.value)
            if 1 <= val <= 100:
                db.update_guild(interaction.guild.id, xp_per_message=val)
                self.view.settings.xp_per_message = val
                self.view._build_container()
                await interaction.response.edit_message(view=self.view)
            else:
                await interaction.response.send_message("XP must be between 1 and 100.", ephemeral=True)
        except:
            await interaction.response.send_message("Invalid number provided.", ephemeral=True)


class LevelingSetupView(ui.LayoutView):
    def __init__(self, bot, user_id: int, settings):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings = settings
        self._build_container()
    
    def _build_container(self):
        self.clear_items()
        self.btn_toggle = ui.Button(
            label="Toggle Leveling", style=discord.ButtonStyle.green if self.settings.leveling_enabled else discord.ButtonStyle.secondary, emoji="⭐", custom_id="toggle_leveling"
        )
        self.btn_toggle.callback = self._on_toggle
        
        self.btn_xp = ui.Button(
            label="Set XP/Message", style=discord.ButtonStyle.blurple, emoji="💬", custom_id="set_xp"
        )
        self.btn_xp.callback = self._on_xp
        
        self.btn_back = ui.Button(label="Back to Menu", style=discord.ButtonStyle.secondary, emoji="◀️", custom_id="btn_back")
        self.btn_back.callback = self._on_back
        
        status = "Enabled" if self.settings.leveling_enabled else "Disabled"
        
        self.container = ui.Container(
            ui.TextDisplay(
                f"## ⭐ Leveling Settings\n\n"
                f"**Status**: {status}\n"
                f"**XP per message**: {self.settings.xp_per_message} XP\n"
                f"**XP Cooldown**: {self.settings.xp_cooldown} seconds"
            ),
            ui.ActionRow(self.btn_toggle, self.btn_xp),
            ui.ActionRow(self.btn_back),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return False
        return True
    
    async def _on_back(self, interaction: discord.Interaction):
        view = SetupSelectView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_toggle(self, interaction: discord.Interaction):
        new_state = not self.settings.leveling_enabled
        db.update_guild(interaction.guild.id, leveling_enabled=new_state)
        self.settings.leveling_enabled = new_state
        self._build_container()
        await interaction.response.edit_message(view=self)
    
    async def _on_xp(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LevelingXpModal(self))


class GiveawaySetupView(ui.LayoutView):
    def __init__(self, bot, user_id: int, settings):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings = settings
        self._build_container()
    
    def _build_container(self):
        self.clear_items()
        self.sel_giveaway_role = ui.RoleSelect(
            placeholder="Select Giveaway Manager Role...", min_values=1, max_values=1, custom_id="sel_gw_role"
        )
        self.sel_giveaway_role.callback = self._on_giveaway_role
        
        self.btn_back = ui.Button(label="Back to Menu", style=discord.ButtonStyle.secondary, emoji="◀️", custom_id="btn_back")
        self.btn_back.callback = self._on_back
        
        role_text = f"<@&{self.settings.giveaway_role_id}>" if self.settings.giveaway_role_id else "Not set"
        
        self.container = ui.Container(
            ui.TextDisplay(f"## 🎁 Giveaway Settings\n\n**Giveaway Manager Role**: {role_text}"),
            ui.ActionRow(self.sel_giveaway_role),
            ui.ActionRow(self.btn_back),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return False
        return True
    
    async def _on_back(self, interaction: discord.Interaction):
        view = SetupSelectView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_giveaway_role(self, interaction: discord.Interaction):
        if not self.sel_giveaway_role.values:
            return await interaction.response.defer()
            
        role_id = self.sel_giveaway_role.values[0].id
        db.update_guild(interaction.guild.id, giveaway_role_id=role_id)
        self.settings.giveaway_role_id = role_id
        self._build_container()
        await interaction.response.edit_message(view=self)


class LoggingSetupView(ui.LayoutView):
    def __init__(self, bot, user_id: int, settings):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings = settings
        self._build_container()
    
    def _build_container(self):
        self.clear_items()
        self.sel_log_channel = ui.ChannelSelect(
            placeholder="Select Log Channel...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1, custom_id="sel_log_ch"
        )
        self.sel_log_channel.callback = self._on_log_channel
        
        self.btn_back = ui.Button(label="Back to Menu", style=discord.ButtonStyle.secondary, emoji="◀️", custom_id="btn_back")
        self.btn_back.callback = self._on_back
        
        channel_text = f"<#{self.settings.log_channel_id}>" if self.settings.log_channel_id else "Not set"
        
        self.container = ui.Container(
            ui.TextDisplay(f"## 📝 Logging Settings\n\n**Log Channel**: {channel_text}"),
            ui.ActionRow(self.sel_log_channel),
            ui.ActionRow(self.btn_back),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return False
        return True
    
    async def _on_back(self, interaction: discord.Interaction):
        view = SetupSelectView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)
    
    async def _on_log_channel(self, interaction: discord.Interaction):
        if not self.sel_log_channel.values:
            return await interaction.response.defer()
            
        channel_id = self.sel_log_channel.values[0].id
        db.update_guild(interaction.guild.id, log_channel_id=channel_id)
        self.settings.log_channel_id = channel_id
        self._build_container()
        await interaction.response.edit_message(view=self)


class WelcomeMessageModal(ui.Modal, title="Edit Welcome Message"):
    message = ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Available tags: {user}, {server}, {member_count}",
        max_length=500
    )
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.message.default = view.settings.welcome_message
        
    async def on_submit(self, interaction: discord.Interaction):
        msg = self.message.value
        db.update_guild(interaction.guild.id, welcome_message=msg)
        self.view.settings.welcome_message = msg
        self.view._build_container()
        await interaction.response.edit_message(view=self.view)


class WelcomeSetupView(ui.LayoutView):
    def __init__(self, bot, user_id: int, settings):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.settings = settings
        self._build_container()
    
    def _build_container(self):
        self.clear_items()
        self.sel_welcome_channel = ui.ChannelSelect(
            placeholder="Select Welcome Channel...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1, custom_id="sel_welc_ch"
        )
        self.sel_welcome_channel.callback = self._on_welcome_channel
        
        self.btn_edit_msg = ui.Button(label="Edit Message", style=discord.ButtonStyle.primary, emoji="✍️", custom_id="btn_edit_msg")
        self.btn_edit_msg.callback = self._on_edit_message
        
        self.btn_back = ui.Button(label="Back to Menu", style=discord.ButtonStyle.secondary, emoji="◀️", custom_id="btn_back")
        self.btn_back.callback = self._on_back
        
        channel_text = f"<#{self.settings.welcome_channel_id}>" if self.settings.welcome_channel_id else "Not set"
        
        self.container = ui.Container(
            ui.TextDisplay(f"## 👋 Welcome Settings\n\n**Welcome Channel**: {channel_text}\n**Welcome Message**:\n> {self.settings.welcome_message}"),
            ui.ActionRow(self.sel_welcome_channel),
            ui.ActionRow(self.btn_edit_msg, self.btn_back),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your menu!", ephemeral=True)
            return False
        return True
    
    async def _on_back(self, interaction: discord.Interaction):
        view = SetupSelectView(self.bot, self.user_id, self.settings)
        await interaction.response.edit_message(view=view)

    async def _on_edit_message(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WelcomeMessageModal(self))
    
    async def _on_welcome_channel(self, interaction: discord.Interaction):
        if not self.sel_welcome_channel.values:
            return await interaction.response.defer()
            
        channel_id = self.sel_welcome_channel.values[0].id
        db.update_guild(interaction.guild.id, welcome_channel_id=channel_id)
        self.settings.welcome_channel_id = channel_id
        self._build_container()
        await interaction.response.edit_message(view=self)


async def setup(bot):
    await bot.add_cog(Setup(bot))