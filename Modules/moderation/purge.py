import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, AdminLogComponent, BaseLayoutView
from Modules.database import db


class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def check_permissions(self, interaction: discord.Interaction) -> str:
        guild = interaction.guild
        actor = interaction.user
        
        if not guild:
            return "This command can only be used in a server."
        
        if not isinstance(actor, discord.Member):
            return "This command can only be used in a server."
        
        if actor.id == guild.owner_id:
            return None
        
        settings = db.get_guild(guild.id)
        if settings.admin_role_id:
            if settings.admin_role_id in [role.id for role in actor.roles]:
                return None
        
        if settings.mod_role_id:
            if settings.mod_role_id in [role.id for role in actor.roles]:
                return None
        
        if actor.guild_permissions.manage_messages:
            return None
        
        return "You don't have permission to manage messages."

    @app_commands.command(name="purge", description="Delete messages in bulk")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.describe(reason="Reason for purging")
    @app_commands.guild_only()
    async def purge_slash(self, interaction: discord.Interaction, amount: int = 10, reason: str = "Bulk delete"):
        # Check channel type
        if not isinstance(interaction.channel, discord.TextChannel):
            embed = EmbedComponent.error("Error", "This can only be used in text channels.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        perm_error = await self.check_permissions(interaction)
        if perm_error:
            embed = EmbedComponent.error("Permission Denied", perm_error)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        amount = max(1, min(100, amount))
        
        cutoff = discord.utils.utcnow() - datetime.timedelta(days=14)
        deleted = await interaction.channel.purge(limit=amount, reason=reason, after=cutoff)
        count = len(deleted)
        
        container = ui.Container(
            ui.TextDisplay(
                f"## 🧹 Channel Purged\n"
                f"Successfully deleted **{count}** recent messages.\n\n"
                f"**Reason:**\n> {reason}"
                + (f"\n\n*Note: Messages older than 14 days were ignored to prevent rate limits.*" if count < amount else "")
            ),
            accent_color=discord.Color.green()
        )
        view = ui.LayoutView()
        view.add_item(container)
        
        await interaction.followup.send(view=view, ephemeral=True)
        
        # Log
        try:
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=interaction.guild,
                action_type="message_delete",
                moderator=interaction.user,
                target=interaction.channel,
                reason=reason,
                extra_info=f"Deleted {count} messages"
            )
        except:
            pass

    @app_commands.command(name="nuke", description="Delete and recreate the current channel")
    @app_commands.guild_only()
    async def nuke_slash(self, interaction: discord.Interaction):
        # Check permissions
        perm_error = await self.check_permissions(interaction)
        if perm_error:
            embed = EmbedComponent.error("Permission Denied", perm_error)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Only text channels can be nuked.", ephemeral=True)
            return

        await interaction.response.send_message("Nuking channel...", ephemeral=True)

        new_channel = await channel.clone(reason=f"Nuke by {interaction.user}")
        await new_channel.edit(position=channel.position)
        
        await channel.delete(reason=f"Nuked by {interaction.user}")
        
        container = ui.Container(
            ui.Section(
                f"## ☢️ Channel Nuked",
                f"This channel has been successfully reset.\n\n"
                f"**Nuked by:** {interaction.user.mention}",
                accessory=ui.Thumbnail(interaction.guild.icon.url if interaction.guild.icon else interaction.user.display_avatar.url)
            ),
            accent_color=discord.Color.red()
        )
        view = ui.LayoutView()
        view.add_item(container)
        await new_channel.send(view=view)
        
        try:
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=interaction.guild,
                action_type="channel_nuke",
                moderator=interaction.user,
                target=new_channel,
                reason="Channel Nuke"
            )
        except:
            pass


async def setup(bot):
    await bot.add_cog(Purge(bot))
