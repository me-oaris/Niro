import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, BaseLayoutView
from Modules.database import db

class WarningHistoryView(BaseLayoutView):
    def __init__(self, user: discord.Member, target: discord.Member, warnings: List[dict]):
        super().__init__(user=user, timeout=180)
        self.target = target
        self.warnings = warnings
        self.build_ui()

    def build_ui(self):
        self.clear_items()
        
        warning_text = ""
        if not self.warnings:
            warning_text = "_This user has a clean record._"
        else:
            for i, warn in enumerate(self.warnings, 1):
                warning_text += f"**{i}.** {warn['reason']}\n> Mod: <@{warn['moderator_id']}>\n\n"

        items = [
            ui.Section(
                f"## 📚 Warning History: {self.target.name}",
                f"Total Warnings: **{len(self.warnings)}**\n\n{warning_text}",
                accessory=ui.Thumbnail(self.target.display_avatar.url)
            )
        ]
        
        if self.warnings:
            options = []
            for i, warn in enumerate(self.warnings, 1):
                label = f"Remove Warning #{i}"
                desc = (warn['reason'][:97] + '...') if len(warn['reason']) > 100 else warn['reason']
                options.append(discord.SelectOption(label=label, description=desc, value=str(warn['id'])))
                
            self.sel_remove = ui.Select(placeholder="Select a warning to remove...", min_values=1, max_values=1, options=options[:25])
            self.sel_remove.callback = self.on_remove_specific
            items.append(ui.ActionRow(self.sel_remove))

        btn_clear = ui.Button(label="Clear All", style=discord.ButtonStyle.danger)
        btn_clear.callback = self.on_clear
        btn_close = ui.Button(label="Close", style=discord.ButtonStyle.secondary)
        btn_close.callback = self.on_close

        items.append(ui.ActionRow(btn_clear, btn_close))
        
        container = ui.Container(*items, accent_color=discord.Color.blurple())
        self.add_item(container)
        
    async def on_remove_specific(self, interaction: discord.Interaction):
        warn_id_str = self.sel_remove.values[0]
        db.remove_warning(interaction.guild.id, int(warn_id_str))
        
        self.warnings = db.get_warnings(interaction.guild.id, self.target.id)
        self.build_ui()
        await interaction.response.edit_message(view=self)

    async def on_clear(self, interaction: discord.Interaction):
        await interaction.response.send_modal(UnwarnConfirmationModal(self.target, interaction.guild.id))
        self.stop()
        
    async def on_close(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(content="❌ Menu closed.", view=None)
        except:
            await interaction.message.delete()
        self.stop()

class UnwarnConfirmationModal(ui.Modal, title="⚠️ Clear Warnings"):
    def __init__(self, target: discord.Member, guild_id: int):
        super().__init__()
        self.target = target
        self.guild_id = guild_id
        
        self.confirm = ui.TextInput(
            label=f"Type 'CONFIRM' to clear {target.name}'s history",
            placeholder="CONFIRM",
            required=True,
            max_length=7
        )
        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "CONFIRM":
            await interaction.response.send_message("❌ Operation cancelled. Confirmation text did not match.", ephemeral=True)
            return
            
        db.clear_warnings(self.guild_id, self.target.id)
        
        container = ui.Container(
            ui.Section(
                "## ✅ History Cleared",
                f"All warnings for **{self.target.mention}** have been successfully removed.",
                accessory=ui.Thumbnail(self.target.display_avatar.url)
            ),
            accent_color=discord.Color.blurple()
        )
        view = ui.LayoutView()
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

class WarningsSelector(BaseLayoutView):
    """View with User Select to browse warnings"""
    def __init__(self, user: discord.Member, mode: str = "view"):
        super().__init__(user=user, timeout=120)
        self.mode = mode # "view" or "clear"
        
        self.user_select = ui.UserSelect(placeholder="Search for a member...", min_values=1, max_values=1)
        self.user_select.callback = self.on_user_selected
        self.btn_close = ui.Button(label="Close", style=discord.ButtonStyle.secondary, custom_id="close_warns")
        self.btn_close.callback = self.on_close
        
        title = "🔍 Search Warnings" if mode == "view" else "🗑️ Clear Warnings"
        desc = "Select a member to view their history." if mode == "view" else "Select a member to clear their entire history."
        
        container = ui.Container(
            ui.TextDisplay(f"## {title}\n{desc}"),
            ui.ActionRow(self.user_select),
            ui.ActionRow(self.btn_close),
            accent_color=discord.Color.blurple()
        )
        self.add_item(container)

    async def on_close(self, interaction: discord.Interaction):
        try:
            await interaction.response.edit_message(content="❌ Menu closed.", view=None)
        except:
            pass
        self.stop()

    async def on_user_selected(self, interaction: discord.Interaction):
        user_id = int(interaction.data["values"][0])
        target = interaction.guild.get_member(user_id)
        
        if not target:
            await interaction.response.send_message("❌ Member not found in this server.", ephemeral=True)
            return

        if self.mode == "view":
            warnings = db.get_warnings(interaction.guild.id, target.id)
            view = WarningHistoryView(interaction.user, target, warnings)
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            await interaction.response.send_modal(UnwarnConfirmationModal(target, interaction.guild.id))

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="warnings", description="View warnings for a member")
    @app_commands.describe(member="The member to view warnings for")
    @app_commands.guild_only()
    async def warnings_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        if member:
            warnings = db.get_warnings(interaction.guild.id, member.id)
            view = WarningHistoryView(interaction.user, member, warnings)
            await interaction.response.send_message(view=view, ephemeral=True)
        else:
            view = WarningsSelector(interaction.user, mode="view")
            await interaction.response.send_message(view=view, ephemeral=True)
    
    @app_commands.command(name="unwarn", description="Clear all warnings from a member")
    @app_commands.describe(member="Member to clear warnings from")
    @app_commands.guild_only()
    async def unwarn_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        if member:
            await interaction.response.send_modal(UnwarnConfirmationModal(member, interaction.guild.id))
        else:
            view = WarningsSelector(interaction.user, mode="clear")
            await interaction.response.send_message(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Warnings(bot))
