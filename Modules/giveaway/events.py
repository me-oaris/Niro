import discord
from discord.ext import commands

active_giveaways = {}


class GiveawayEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in active_giveaways:
            return
        
        if payload.user_id == self.bot.user.id:
            return
        
        giveaway = active_giveaways[payload.message_id]
        
        emoji_str = str(payload.emoji)
        giveaway_emoji = giveaway.get("emoji", "🎉")
        
        if emoji_str == giveaway_emoji:
            user_id = payload.user_id
            if user_id not in giveaway["entries"]:
                giveaway["entries"].append(user_id)
                print(f"User {user_id} entered giveaway {payload.message_id}. Total entries: {len(giveaway['entries'])}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id not in active_giveaways:
            return
        
        if payload.user_id == self.bot.user.id:
            return
        
        giveaway = active_giveaways[payload.message_id]
        
        emoji_str = str(payload.emoji)
        giveaway_emoji = giveaway.get("emoji", "🎉")
        
        if emoji_str == giveaway_emoji:
            user_id = payload.user_id
            if user_id in giveaway["entries"]:
                giveaway["entries"].remove(user_id)
                print(f"User {user_id} left giveaway {payload.message_id}. Total entries: {len(giveaway['entries'])}")


async def setup(bot):
    await bot.add_cog(GiveawayEvents(bot))
