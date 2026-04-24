from .ban import setup as ban_setup
from .kick import setup as kick_setup
from .lock import setup as lock_setup
from .mute import setup as mute_setup
from .purge import setup as purge_setup
from .unlock import setup as unlock_setup
from .warn import setup as warn_setup
from .warnings import setup as warnings_setup
from .events import setup as events_setup

async def setup(bot):
    await ban_setup(bot)
    await kick_setup(bot)
    await lock_setup(bot)
    await mute_setup(bot)
    await purge_setup(bot)
    await unlock_setup(bot)
    await warn_setup(bot)
    await warnings_setup(bot)
    await events_setup(bot)
