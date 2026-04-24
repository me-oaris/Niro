from .ping import setup as ping_setup
from .uptime import setup as uptime_setup

async def setup(bot):
    await ping_setup(bot)
    await uptime_setup(bot)
