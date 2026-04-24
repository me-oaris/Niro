"""
Leveling Module
"""

from .commands import setup as commands_setup
from .events import setup as events_setup

async def setup(bot):
    await commands_setup(bot)
    await events_setup(bot)
