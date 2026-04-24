import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('niro')

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True

GUILD_ID = os.getenv("GUILD_ID")

class Niro(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=None
        )
        self.module_dirs = [
            'Modules.moderation', 
            'Modules.utility',
            'Modules.leveling',
            'Modules.giveaway'
        ]
        self.module_files = ['Modules.setup']

    async def setup_hook(self):
        extensions = self.module_dirs + self.module_files
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f'Loaded extension: {extension}')
            except Exception as e:
                logger.error(f'Failed to load extension {extension}: {e}')

        # Sync commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

    async def on_ready(self):
        logger.info(f"🚀 {self.user} is online and ready!")
        await self.change_presence(activity=discord.Game(name="Niro Bot | /help"))

niro = Niro()

async def main():
    async with niro:
        token = os.getenv("TOKEN")
        if not token:
            logger.error("No TOKEN found in .env file!")
            return
        await niro.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

