import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, AdminLogComponent, BaseLayoutView
from Modules.database import db

class KickReasonModal(ui.Modal, title="👢 Kick Confirmation"):
    reason = ui.TextInput(
        label="Reason", 
        style=discord.TextStyle.paragraph, 
        placeholder="Enter a reason for kicking...", 
        required=True,
        default="Breaking server rules"
    )

    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Kick'):
        super().__init__()
        self.target = target
        self.actor = actor
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        result = await self.cog.run_kick(interaction, self.target, self.reason.value)
        if result:
            await interaction.followup.send(content=f"❌ {result}", ephemeral=True)

class KickConfirmView(BaseLayoutView):
    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Kick'):
        super().__init__(user=actor, timeout=60)
        self.target = target
        self.actor = actor
        self.cog = cog
        
        btn_confirm = ui.Button(label="Proceed to Kick", style=discord.ButtonStyle.danger, emoji="👢")
        btn_confirm.callback = self.on_confirm
        
        btn_cancel = ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        btn_cancel.callback = self.on_cancel
        
        container = ui.Container(
            ui.Section(
                f"## 👢 Kick {self.target.name}?",
                f"You are about to kick **{self.target.mention}** from the server.\n"
                f"They will be able to rejoin via an invite link.",
                accessory=ui.Thumbnail(self.target.display_avatar.url)
            ),
            ui.ActionRow(btn_confirm, btn_cancel),
            accent_color=discord.Color.blurple()
        )
        self.add_item(container)

    async def on_confirm(self, interaction: discord.Interaction):
        await interaction.response.send_modal(KickReasonModal(self.target, self.actor, self.cog))
        self.stop()

    async def on_cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Kick cancelled.", view=None)
        self.stop()

class Kick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def run_kick(
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
                    f"## 👢 Kicked from {guild.name}",
                    f"You have been kicked for the following reason:\n> {reason}",
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
            await target.kick(reason=f"{reason} | Moderator: {actor} ({actor.id})")
            
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=guild,
                action_type="kick",
                moderator=actor,
                target=target,
                reason=reason
            )
            
            view = BaseLayoutView(actor)
            container = ui.Container(
                ui.Section(
                    f"## ✅ Successfully Kicked\n"
                    f"**{target.name}** has been removed.",
                    accessory=ui.Thumbnail(target.display_avatar.url)
                ),
                ui.Separator(),
                ui.TextDisplay(
                    f"**Reason:**\n> {reason}\n\n"
                    f"**Metadata:**\n"
                    f"- Moderator: {actor.mention}\n"
                    f"- DM Status: {'Sent ✅' if dm_sent else 'Failed ❌'}"
                ),
                accent_color=discord.Color.blurple()
            )
            view.add_item(container)
            await interaction.followup.send(view=view)
            return None
        except Exception as e:
            return f"Kick failed: {str(e)}"

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick")
    @app_commands.guild_only()
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id != interaction.guild.owner_id:
            if member.top_role.position >= interaction.user.top_role.position:
                embed = EmbedComponent.error("Cannot Kick", "You cannot kick someone with a higher or equal role.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        view = KickConfirmView(member, interaction.user, self)
        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Kick(bot))
