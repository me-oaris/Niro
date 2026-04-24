import discord
from discord.ext import commands
from discord import app_commands
import time
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components.embed_component import EmbedComponent


class Uptime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
    
    def get_uptime(self) -> str:
        uptime = time.time() - self.start_time
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def get_uptime_details(self) -> dict:
        uptime = time.time() - self.start_time
        days = int(uptime // 86400)
        hours = int((uptime % 86400) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        return {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "total_seconds": uptime
        }
    
    @app_commands.command(name="uptime", description="Check bot uptime")
    async def uptime_slash(self, interaction: discord.Interaction):
        uptime_details = self.get_uptime_details()
        
        embed = EmbedComponent.info(
            title="📡 Bot Uptime",
            description=f"**{self.get_uptime()}**",
            fields=[
                ("Days", str(uptime_details["days"]), True),
                ("Hours", str(uptime_details["hours"]), True),
                ("Minutes", str(uptime_details["minutes"]), True),
                ("Seconds", str(uptime_details["seconds"]), True),
            ],
            timestamp=True
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Uptime(bot))
