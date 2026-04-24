import discord
from discord.ext import commands
from discord import app_commands
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components.embed_component import EmbedComponent

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        
        if latency < 100:
            embed = EmbedComponent.success(
                title="Faah!",
                description=f"Latency: **{latency/10}ms**"
            )
        elif latency < 200:
            embed = EmbedComponent.warning(
                title="Faah!",
                description=f"Latency: **{latency/10}ms**"
            )
        else:
            embed = EmbedComponent.error(
                title="Faah!!",
                description=f"Latency: **{latency/10}ms**"
            )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Ping(bot))