import discord
from discord.ext import commands

class ModerationEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id")
        if not custom_id: return

        from Components import AdminLogComponent
        log = AdminLogComponent(self.bot)

        if custom_id.startswith("unban_"):
            try:
                user_id = int(custom_id.split("_")[1])
                await interaction.response.defer(ephemeral=True)
                await interaction.guild.unban(discord.Object(id=user_id))
                await interaction.followup.send(f"✅ User <@{user_id}> has been successfully unbanned.", ephemeral=True)
                
                await log.log_action(
                    guild=interaction.guild,
                    action_type="unban",
                    moderator=interaction.user,
                    target=discord.Object(id=user_id),
                    reason="Undo Ban button click"
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to unban: {e}", ephemeral=True)

        elif custom_id == "view_level_stats":
            await interaction.response.defer(ephemeral=True)
            leveling_cog = self.bot.get_cog("LevelingCommands")
            if leveling_cog:
                await leveling_cog.send_level_card(interaction, interaction.user)
            else:
                await interaction.followup.send("❌ Leveling system is currently unavailable.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot: return
        if not message.guild: return
        
        from Components import AdminLogComponent
        log = AdminLogComponent(self.bot)
        await log.log_message_delete(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot: return
        if not before.guild: return
        if before.content == after.content: return
        
        from Components import AdminLogComponent
        log = AdminLogComponent(self.bot)
        await log.log_message_edit(before, after)

async def setup(bot):
    await bot.add_cog(ModerationEvents(bot))
