import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, BaseLayoutView
from Modules.database import db

BACKGROUND_PRESETS = {
    "default": {"name": "Blurple", "bg": (30, 30, 35), "accent": (88, 101, 242)},
    "purple": {"name": "Purple", "bg": (45, 30, 60), "accent": (155, 89, 182)},
    "red": {"name": "Red", "bg": (60, 30, 30), "accent": (192, 57, 43)},
    "green": {"name": "Green", "bg": (30, 60, 45), "accent": (46, 204, 113)},
    "gold": {"name": "Gold", "bg": (60, 50, 30), "accent": (241, 196, 15)},
    "pink": {"name": "Pink", "bg": (60, 30, 50), "accent": (233, 69, 96)},
    "ocean": {"name": "Ocean", "bg": (30, 50, 60), "accent": (0, 116, 217)},
}

def hex_to_rgb(hex_str: str) -> Optional[tuple]:
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        try:
            return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
        except:
            return None
    return None

class ColorPersonalizeModal(ui.Modal, title="Personalize Rank Card"):
    color_input = ui.TextInput(
        label="Theme or Hex Color",
        placeholder="e.g. Blurple, Gold, Red or #FF0000",
        min_length=2,
        max_length=20
    )
    
    def __init__(self, original_interaction: discord.Interaction, cog: 'LevelingCommands'):
        super().__init__()
        self.original_interaction = original_interaction
        self.cog = cog
        
    async def on_submit(self, interaction: discord.Interaction):
        value = self.color_input.value.strip().lower()
        
        preset = None
        for k, v in BACKGROUND_PRESETS.items():
            if value == k or value == v['name'].lower():
                preset = k
                break
        
        if preset:
            db.set_user_card_color(interaction.user.id, preset)
        else:
            rgb = hex_to_rgb(value)
            if rgb:
                db.set_user_card_color(interaction.user.id, value if value.startswith('#') else f"#{value}")
            else:
                await interaction.response.send_message("Invalid color! Use a theme name (Blurple, Red...) or a Hex code (#FF0000).", ephemeral=True)
                return
        
        await interaction.response.defer()
        await self.cog.send_level_card(self.original_interaction, interaction.user, edit=True)
        await interaction.followup.send("✅ Rank card updated!", ephemeral=True)

class LevelingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def send_level_card(self, interaction: discord.Interaction, user: discord.Member, edit: bool = False):
        guild_id = interaction.guild.id
        card_color = db.get_user_card_color(user.id)
        
        if card_color.startswith('#'):
            rgb = hex_to_rgb(card_color)
            if not rgb: rgb = BACKGROUND_PRESETS["default"]["accent"]
            bg = {"name": "Custom", "bg": (20, 20, 25), "accent": rgb}
        else:
            bg = BACKGROUND_PRESETS.get(card_color, BACKGROUND_PRESETS["default"])
            
        progress = db.get_level_progress(guild_id, user.id)
        leaderboard = db.get_leaderboard(guild_id, limit=100)
        rank = next((i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == user.id), None)
        
        try:
            card_file = await EmbedComponent.create_level_card(
                user=user,
                level=progress['level'],
                xp=progress['xp'],
                xp_needed=progress['next_level_xp'],
                progress=progress['progress'],
                rank=rank,
                background_color=bg["bg"],
                accent_color=bg["accent"]
            )
            
            view = BaseLayoutView(interaction.user)
            children = [
                ui.MediaGallery(discord.MediaGalleryItem(media=card_file))
            ]

            if user.id == interaction.user.id:
                btn_color = ui.Button(label="Personalize Card", style=discord.ButtonStyle.secondary, emoji="🎨")
                async def change_color_callback(it: discord.Interaction):
                    await it.response.send_modal(ColorPersonalizeModal(interaction, self))
                btn_color.callback = change_color_callback
                children.append(ui.ActionRow(btn_color))

            container = ui.Container(
                *children,
                accent_color=discord.Color.from_rgb(*bg["accent"])
            )
            view.add_item(container)

            if edit:
                await interaction.edit_original_response(attachments=[card_file], view=view)
            elif interaction.response.is_done():
                await interaction.followup.send(file=card_file, view=view)
            else:
                await interaction.response.send_message(file=card_file, view=view)
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="level", description="View your or someone else's level")
    @app_commands.describe(user="The user to view")
    @app_commands.guild_only()
    async def level_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        user = user or interaction.user
        await self.send_level_card(interaction, user)

    @app_commands.command(name="leaderboard", description="View the server leaderboard")
    @app_commands.guild_only()
    async def lb_command(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        leaderboard = db.get_leaderboard(guild_id)
        
        if not leaderboard:
            return await interaction.response.send_message("No one has gained any XP yet!", ephemeral=True)
            
        embed = EmbedComponent.leaderboard(interaction.guild, leaderboard)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(LevelingCommands(bot))
