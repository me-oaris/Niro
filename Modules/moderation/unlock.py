import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, AdminLogComponent, BaseLayoutView
from Modules.database import db


class Unlock(commands.Cog):
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
        
        if actor.guild_permissions.manage_channels:
            return None
        
        return "You don't have permission to manage channels."

    @app_commands.command(name="unlock", description="Unlock this channel")
    @app_commands.describe(reason="Reason for unlocking")
    @app_commands.guild_only()
    async def unlock_slash(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        perm_error = await self.check_permissions(interaction)
        if perm_error:
            embed = EmbedComponent.error("Permission Denied", perm_error)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        channel = interaction.channel
        
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = None
            overwrite.add_reactions = None
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            
            view = BaseLayoutView(interaction.user)
            container = ui.Container(
                ui.Section(
                    f"## 🔓 Channel Unlocked",
                    f"This channel has been successfully restored.\n\n"
                    f"**Reason:**\n> {reason}\n\n"
                    f"**Moderator:** {interaction.user.mention}",
                    accessory=ui.Thumbnail(interaction.guild.icon.url if interaction.guild.icon else interaction.user.display_avatar.url)
                ),
                accent_color=discord.Color.blurple()
            )
            view.add_item(container)
            await interaction.response.send_message(view=view)
            
            admin_log = AdminLogComponent(self.bot)
            await admin_log.log_action(
                guild=interaction.guild,
                action_type="unlock",
                moderator=interaction.user,
                target=channel,
                reason=reason
            )
        except Exception as e:
            embed = EmbedComponent.error("Unlock Failed", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Unlock(bot))
