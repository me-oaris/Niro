import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
import sys
import os
import datetime
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, AdminLogComponent, BaseLayoutView
from Modules.database import db

def parse_duration(duration_str: str) -> Optional[datetime.timedelta]:
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    match = re.fullmatch(r'(\d+)([smhdw])', duration_str.lower())
    if not match: return None
    val, unit = match.groups()
    return datetime.timedelta(seconds=int(val) * units[unit])

class MuteModal(ui.Modal, title="🔇 Timeout Confirmation"):
    duration = ui.TextInput(label="Duration (e.g. 10m, 1h, 1d)", placeholder="10m, 1h, 1d", default="1h", max_length=10)
    reason = ui.TextInput(label="Reason", style=discord.TextStyle.paragraph, placeholder="Enter a reason...", required=True)

    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Mute'):
        super().__init__()
        self.target = target
        self.actor = actor
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        result = await self.cog.run_mute(interaction, self.target, self.reason.value, self.duration.value)
        if result:
            await interaction.response.send_message(content=f"❌ {result}", ephemeral=True)

class MuteConfirmView(BaseLayoutView):
    def __init__(self, target: discord.Member, actor: discord.Member, cog: 'Mute'):
        super().__init__(user=actor, timeout=60)
        self.target = target
        self.actor = actor
        self.cog = cog
        
        btn_confirm = ui.Button(label="Proceed to Timeout", style=discord.ButtonStyle.danger, emoji="🔇")
        btn_confirm.callback = self.on_confirm
        
        btn_cancel = ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        btn_cancel.callback = self.on_cancel
        
        container = ui.Container(
            ui.Section(
                f"## 🔇 Timeout {self.target.name}?",
                f"You are about to place **{self.target.mention}** in timeout.\n"
                f"They will be unable to send messages during this period.",
                accessory=ui.Thumbnail(self.target.display_avatar.url)
            ),
            ui.ActionRow(btn_confirm, btn_cancel),
            accent_color=discord.Color.blurple()
        )
        self.add_item(container)

    async def on_confirm(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MuteModal(self.target, self.actor, self.cog))
        self.stop()

    async def on_cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Timeout cancelled.", view=None)
        self.stop()

class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def run_mute(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        duration_str: str = "1h"
    ) -> str:
        guild = interaction.guild
        actor = interaction.user
        
        duration = parse_duration(duration_str)
        if not duration:
            return f"Invalid duration format: `{duration_str}`. Use 10m, 1h, 1d, etc."

        dm_sent = False
        try:
            container = ui.Container(
                ui.Section(
                    f"## 🔇 Timed Out in {guild.name}",
                    f"You have been restricted for **{duration_str}**.\n**Reason:** {reason}",
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
            await target.timeout(duration, reason=f"{reason} | Moderator: {actor} ({actor.id})")
            
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=guild,
                action_type="mute",
                moderator=actor,
                target=target,
                reason=reason,
                duration=duration_str
            )
            
            view = BaseLayoutView(actor)
            btn_unmute = ui.Button(label="Unmute Now", style=discord.ButtonStyle.secondary, emoji="🔊")
            
            async def unmute_callback(btn_interaction):
                if btn_interaction.user.id != actor.id and btn_interaction.user.id != guild.owner_id:
                    return await btn_interaction.response.send_message("You cannot do this.", ephemeral=True)
                
                await target.timeout(None)
                btn_unmute.disabled = True
                
                log = AdminLogComponent(self.bot)
                await log.log_action(
                    guild=guild,
                    action_type="unmute",
                    moderator=btn_interaction.user,
                    target=target,
                    reason="Manual unmute via button"
                )
                
                view.clear_items()
                new_container = ui.Container(
                    ui.Section(
                        f"## 🔊 Timeout Removed",
                        f"**{target.name}** was manually unmuted.\n\n"
                        f"**Unmuted by:** {btn_interaction.user.mention}",
                        accessory=ui.Thumbnail(target.display_avatar.url)
                    ),
                    ui.ActionRow(btn_unmute),
                    accent_color=discord.Color.dark_theme()
                )
                view.add_item(new_container)
                await btn_interaction.response.edit_message(content=None, view=view)
                
            btn_unmute.callback = unmute_callback
            
            container = ui.Container(
                ui.Section(
                    f"## ✅ Successfully Restricted",
                    f"**{target.name}** is now in timeout.\n\n"
                    f"**Reason:**\n> {reason}\n"
                    f"**Duration:** {duration_str}\n\n"
                    f"**Metadata:**\n"
                    f"- Moderator: {actor.mention}\n"
                    f"- DM Status: {'Sent ✅' if dm_sent else 'Failed ❌'}",
                    accessory=ui.Thumbnail(target.display_avatar.url)
                ),
                ui.ActionRow(btn_unmute),
                accent_color=discord.Color.blurple()
            )
            view.add_item(container)
            await interaction.response.edit_message(content=None, view=view)
            return None
        except Exception as e:
            return f"Timeout failed: {str(e)}"

    @app_commands.command(name="mute", description="Place a member in timeout")
    @app_commands.describe(member="The member to mute")
    @app_commands.guild_only()
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member):
        if interaction.user.id != interaction.guild.owner_id:
            if member.top_role.position >= interaction.user.top_role.position:
                embed = EmbedComponent.error("Cannot Timeout", "You cannot timeout someone with a higher or equal role.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        view = MuteConfirmView(member, interaction.user, self)
        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Mute(bot))
