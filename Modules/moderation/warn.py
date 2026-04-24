import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, AdminLogComponent, BaseLayoutView
from Modules.database import db

class WarnModal(ui.Modal, title="⚠️ Warning Confirmation"):
    reason = ui.TextInput(
        label="Reason", 
        style=discord.TextStyle.paragraph, 
        placeholder="Enter a reason for the warning...", 
        required=True,
        default="Minor server rule violation"
    )

    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Warn'):
        super().__init__()
        self.target = target
        self.actor = actor
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        result = await self.cog.run_warn(interaction, self.target, self.reason.value)
        if result:
            await interaction.response.send_message(content=f"❌ {result}", ephemeral=True)

class WarnConfirmView(BaseLayoutView):
    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Warn'):
        super().__init__(user=actor, timeout=60)
        self.target = target
        self.actor = actor
        self.cog = cog
        
        btn_confirm = ui.Button(label="Proceed to Warn", style=discord.ButtonStyle.danger, emoji="⚠️")
        btn_confirm.callback = self.on_confirm
        
        btn_cancel = ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        btn_cancel.callback = self.on_cancel
        
        container = ui.Container(
            ui.Section(
                f"## ⚠️ Warn {self.target.name}?",
                f"You are about to issue a formal warning to **{self.target.mention}**.\n"
                f"This will be recorded in their history.",
                accessory=ui.Thumbnail(self.target.display_avatar.url)
            ),
            ui.ActionRow(btn_confirm, btn_cancel),
            accent_color=discord.Color.blurple()
        )
        self.add_item(container)

    async def on_confirm(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WarnModal(self.target, self.actor, self.cog))
        self.stop()

    async def on_cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Warning cancelled.", view=None)
        self.stop()

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def run_warn(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
    ) -> str:
        guild = interaction.guild
        actor = interaction.user
        
        dm_sent = False
        try:
            container = ui.Container(
                ui.Section(
                    f"## ⚠️ Warned in {guild.name}",
                    f"You have received a formal warning for:\n> {reason}",
                    accessory=ui.Thumbnail(guild.icon.url if guild.icon else None)
                ),
                accent_color=discord.Color.blurple()
            )
            view = ui.LayoutView()
            view.add_item(container)
            await target.send(view=view)
            dm_sent = True
        except:
            dm_sent = False

        try:
            # Add warning to database
            warn_id = db.add_warning(guild.id, target.id, reason, actor.id)
            warnings = db.get_warnings(guild.id, target.id)
            warning_count = len(warnings)
            
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=guild,
                action_type="warn",
                moderator=actor,
                target=target,
                reason=reason
            )
            
            view = BaseLayoutView(actor)
            btn_history = ui.Button(label="View Warnings", style=discord.ButtonStyle.secondary, emoji="📚")
            
            async def history_callback(btn_interaction):
                from Modules.moderation.warnings import WarningHistoryView
                warnings = db.get_warnings(guild.id, target.id)
                v = WarningHistoryView(btn_interaction.user, target, warnings)
                await btn_interaction.response.send_message(view=v, ephemeral=True)
                
            btn_history.callback = history_callback
            
            container = ui.Container(
                ui.Section(
                    f"## ✅ Successfully Warned",
                    f"**{target.name}** now has **{warning_count}** warning(s).\n\n"
                    f"**Reason:**\n> {reason}\n\n"
                    f"**Metadata:**\n"
                    f"- Moderator: {actor.mention}\n"
                    f"- Warning ID: `{warn_id}`",
                    accessory=ui.Thumbnail(target.display_avatar.url)
                ),
                ui.ActionRow(btn_history),
                accent_color=discord.Color.blurple()
            )
            view.add_item(container)
            await interaction.response.edit_message(content=None, view=view)
            return None
        except Exception as e:
            return f"Warn failed: {str(e)}"

    @app_commands.command(name="warn", description="Issue a warning to a member")
    @app_commands.describe(member="The member to warn")
    @app_commands.guild_only()
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id != interaction.guild.owner_id:
            if member.top_role.position >= interaction.user.top_role.position:
                embed = EmbedComponent.error("Cannot Warn", "You cannot warn someone with a higher or equal role.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        view = WarnConfirmView(member, interaction.user, self)
        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Warn(bot))
