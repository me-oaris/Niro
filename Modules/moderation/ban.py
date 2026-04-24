import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, AdminLogComponent, BaseLayoutView
from Modules.database import db

class BanReasonModal(ui.Modal, title="🔨 Ban Confirmation"):
    reason = ui.TextInput(
        label="Reason", 
        style=discord.TextStyle.paragraph, 
        placeholder="Enter a reason for the ban...", 
        required=True,
        default="Breaking server rules"
    )
    delete_days = ui.TextInput(
        label="Delete History (Days)", 
        placeholder="0-7", 
        default="1", 
        max_length=1
    )

    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Ban'):
        super().__init__()
        self.target = target
        self.actor = actor
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.delete_days.value)
            if not 0 <= days <= 7: days = 1
        except:
            days = 1
            
        await interaction.response.defer(ephemeral=True)
        result = await self.cog.run_ban(interaction, self.target, self.reason.value, days)
        if result:
            await interaction.followup.send(content=f"❌ {result}", ephemeral=True)

class BanConfirmView(BaseLayoutView):
    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Ban'):
        super().__init__(user=actor, timeout=60)
        self.target = target
        self.actor = actor
        self.cog = cog
        
        btn_confirm = ui.Button(label="Proceed to Ban", style=discord.ButtonStyle.danger, emoji="🔨")
        btn_confirm.callback = self.on_confirm
        
        btn_cancel = ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        btn_cancel.callback = self.on_cancel
        
        container = ui.Container(
            ui.Section(
                f"## 🔨 Ban {self.target.name}?",
                f"You are about to ban **{self.target.mention}** from this server.\n"
                f"This action is permanent unless revoked.",
                accessory=ui.Thumbnail(self.target.display_avatar.url)
            ),
            ui.ActionRow(btn_confirm, btn_cancel),
            accent_color=discord.Color.blurple()
        )
        self.add_item(container)

    async def on_confirm(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BanReasonModal(self.target, self.actor, self.cog))
        self.stop()

    async def on_cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Ban cancelled.", view=None)
        self.stop()

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def run_ban(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        delete_days: int = 1,
    ) -> str:
        guild = interaction.guild
        actor = interaction.user
        
        dm_sent = False
        try:
            dm_container = ui.Container(
                ui.Section(
                    f"## 🔨 Banned from {guild.name}",
                    f"You have been banned for the following reason:\n> {reason}",
                    accessory=ui.Thumbnail(guild.icon.url if guild.icon else None)
                ),
                accent_color=discord.Color.blurple()
            )
            dm_view = ui.LayoutView()
            dm_view.add_item(dm_container)
            await target.send(view=dm_view)
            dm_sent = True
        except:
            dm_sent = False

        try:
            await target.ban(delete_message_days=delete_days, reason=f"{reason} | Moderator: {actor} ({actor.id})")
            
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=guild,
                action_type="ban",
                moderator=actor,
                target=target,
                reason=reason,
                duration=f"{delete_days} days"
            )
            
            view = BaseLayoutView(actor)
            btn_unban = ui.Button(label="Undo Ban", style=discord.ButtonStyle.secondary, emoji="↩️", custom_id=f"unban_{target.id}")
            
            container = ui.Container(
                ui.Section(
                    f"## ✅ Successfully Banned\n"
                    f"**{target.name}** has been removed from the server.",
                    accessory=ui.Thumbnail(target.display_avatar.url)
                ),
                ui.Separator(),
                ui.TextDisplay(
                    f"**Reason:**\n> {reason}\n\n"
                    f"**Metadata:**\n"
                    f"- Moderator: {actor.mention}\n"
                    f"- History Deleted: {delete_days} days\n"
                    f"- DM Status: {'Sent ✅' if dm_sent else 'Failed ❌'}"
                ),
                ui.ActionRow(btn_unban),
                accent_color=discord.Color.blurple()
            )
            view.add_item(container)
            await interaction.followup.send(view=view)
            return None
        except Exception as e:
            return f"Ban failed: {str(e)}"

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban")
    @app_commands.guild_only()
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id != interaction.guild.owner_id:
            if member.top_role.position >= interaction.user.top_role.position:
                embed = EmbedComponent.error("Cannot Ban", "You cannot ban someone with a higher or equal role.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        view = BanConfirmView(member, interaction.user, self)
        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ban(bot))
