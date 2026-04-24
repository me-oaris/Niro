import discord
from discord.ext import commands
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent, BaseLayoutView
from discord import ui
from Modules.database import db


class LevelingEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}
    
    async def check_leveling_enabled(self, guild_id: int) -> bool:
        settings = db.get_guild(guild_id)
        return settings.leveling_enabled
    
    async def add_xp(self, guild_id: int, user_id: int, xp: int):
        settings = db.get_guild(guild_id)
        
        if not settings.leveling_enabled:
            return 0, 0, False
        
        cooldown_key = (guild_id, user_id)
        now = datetime.now().timestamp()
        
        if cooldown_key in self.xp_cooldowns:
            last_time = self.xp_cooldowns[cooldown_key]
            if now - last_time < settings.xp_cooldown:
                return 0, 0, False
        
        xp_gained, new_level = db.add_xp(guild_id, user_id, xp)
        
        self.xp_cooldowns[cooldown_key] = now
        
        current_level = db.get_user_level(guild_id, user_id).level
        xp_gained, new_level = db.add_xp(guild_id, user_id, xp)
        
        self.xp_cooldowns[cooldown_key] = now
        leveled_up = new_level > current_level
        
        return xp_gained, new_level, leveled_up
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        if not await self.check_leveling_enabled(message.guild.id):
            return
        
        settings = db.get_guild(message.guild.id)
        
        xp_gained, new_level, leveled_up = await self.add_xp(
            message.guild.id,
            message.author.id,
            settings.xp_per_message
        )
        
        db.add_message(message.guild.id, message.author.id)
        
        if leveled_up and xp_gained > 0:
            try:
                settings = db.get_guild(message.guild.id)
                if settings.leveling_enabled:
                    leveling_cog = self.bot.get_cog("LevelingCommands")
                    if leveling_cog:
                        card_color = db.get_user_card_color(message.author.id)
                        bg = leveling_cog.BACKGROUND_PRESETS.get(card_color, {"accent": (88, 101, 242)})
                        progress = db.get_level_progress(message.guild.id, message.author.id)
                        leaderboard = db.get_leaderboard(message.guild.id, limit=100)
                        rank = next((i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == message.author.id), None)
                        
                        card_file = await EmbedComponent.create_level_card(
                            user=message.author,
                            level=new_level,
                            xp=progress['xp'],
                            xp_needed=progress['next_level_xp'],
                            progress=progress['progress'],
                            rank=rank,
                            accent_color=bg["accent"]
                        )
                        
                        from Components import BaseLayoutView
                        view = BaseLayoutView(message.author)
                        
                        container = discord.ui.Container(
                            discord.ui.Section(
                                f"## 🎉 Level Up!\n"
                                f"Congratulations {message.author.mention}! You've reached **Level {new_level}**.",
                                accessory=discord.ui.Thumbnail(message.author.display_avatar.url)
                            ),
                            discord.ui.MediaGallery(discord.MediaGalleryItem(media=card_file)),


                            discord.ui.ActionRow(
                                discord.ui.Button(label="View Level Stats", style=discord.ButtonStyle.blurple, emoji="📊", custom_id="view_level_stats")
                            ),
                            accent_color=discord.Color.from_rgb(*bg["accent"])
                        )
                        view.add_item(container)
                        await message.channel.send(file=card_file, view=view)

            except:
                pass


async def setup(bot):
    await bot.add_cog(LevelingEvents(bot))
