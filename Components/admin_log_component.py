import discord
from datetime import datetime
from typing import Optional, List
from discord import TextChannel, Thread


class AdminLogComponent:
    
    ACTION_WARN = "warn"
    ACTION_KICK = "kick"
    ACTION_BAN = "ban"
    ACTION_UNBAN = "unban"
    ACTION_MUTE = "mute"
    ACTION_UNMUTE = "unmute"
    ACTION_TIMEOUT = "timeout"
    ACTION_DELETE = "message_delete"
    ACTION_EDIT = "message_edit"
    ACTION_LOCK = "lock"
    ACTION_UNLOCK = "unlock"
    ACTION_NUKE = "channel_nuke"
    
    ACTION_COLORS = {
        ACTION_WARN: discord.Color.orange(),
        ACTION_KICK: discord.Color.red(),
        ACTION_BAN: discord.Color.dark_red(),
        ACTION_UNBAN: discord.Color.green(),
        ACTION_MUTE: discord.Color.yellow(),
        ACTION_UNMUTE: discord.Color.green(),
        ACTION_TIMEOUT: discord.Color.orange(),
        ACTION_DELETE: discord.Color.red(),
        ACTION_EDIT: discord.Color.blue(),
        ACTION_LOCK: discord.Color.purple(),
        ACTION_UNLOCK: discord.Color.green(),
        ACTION_NUKE: discord.Color.dark_magenta(),
    }
    
    def __init__(self, bot: discord.Client):
        self.bot = bot
    
    async def get_log_channel(self, guild: discord.Guild) -> Optional[TextChannel]:
        from Modules.database import db
        settings = db.get_guild(guild.id)
        if settings and settings.log_channel_id:
            channel = guild.get_channel(settings.log_channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                return channel
                
        channel_names = ["admin-logs", "mod-logs", "logs", "audit-logs"]
        
        for channel_name in channel_names:
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            if channel:
                return channel
        return None
    
    async def log_action(
        self,
        guild: discord.Guild,
        action_type: str,
        moderator: discord.Member,
        target: discord.Member,
        reason: str = "No reason provided",
        duration: Optional[str] = None,
        extra_info: Optional[str] = None
    ) -> Optional[discord.Message]:
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return None
        
        embed = discord.Embed(
            title=f"Action: {action_type.replace('_', ' ').title()}",
            color=self.ACTION_COLORS.get(action_type, discord.Color.light_grey()),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Target", value=target.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        
        if extra_info:
            embed.add_field(name="Additional Info", value=extra_info, inline=False)
        
        embed.set_footer(text=f"User ID: {target.id} | Moderator ID: {moderator.id}")
        
        return await log_channel.send(embed=embed)
    
    async def log_message_delete(
        self,
        message: discord.Message,
        moderator: Optional[discord.Member] = None
    ) -> Optional[discord.Message]:
        guild = message.guild
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return None
        
        embed = discord.Embed(
            title="Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        
        if moderator:
            embed.add_field(name="Deleted By", value=moderator.mention, inline=True)
        
        content = message.content or "*No text content*"
        if len(content) > 1024:
            content = content[:1021] + "..."
        embed.add_field(name="Content", value=content, inline=False)
        
        embed.set_footer(text=f"Message ID: {message.id} | Author ID: {message.author.id}")
        
        return await log_channel.send(embed=embed)
    
    async def log_message_edit(
        self,
        before: discord.Message,
        after: discord.Message
    ) -> Optional[discord.Message]:
        guild = before.guild
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return None
        
        embed = discord.Embed(
            title="Message Edited",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        
        before_content = before.content or "*No text content*"
        after_content = after.content or "*No text content*"
        
        if len(before_content) > 512:
            before_content = before_content[:509] + "..."
        if len(after_content) > 512:
            after_content = after_content[:509] + "..."
        
        embed.add_field(name="Before", value=before_content, inline=False)
        embed.add_field(name="After", value=after_content, inline=False)
        
        embed.set_footer(text=f"Message ID: {before.id} | Author ID: {before.author.id}")
        
        return await log_channel.send(embed=embed)
    
    async def log_member_join(
        self,
        member: discord.Member
    ) -> Optional[discord.Message]:
        guild = member.guild
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return None
        
        embed = discord.Embed(
            title="Member Joined",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        member_count = len([m for m in guild.members if not m.bot])
        embed.add_field(name="Member Count", value=str(member_count), inline=True)
        
        return await log_channel.send(embed=embed)
    
    async def log_member_leave(
        self,
        member: discord.Member
    ) -> Optional[discord.Message]:
        guild = member.guild
        log_channel = await self.get_log_channel(guild)
        if not log_channel:
            return None
        
        embed = discord.Embed(
            title="Member Left",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Member", value=member.mention, inline=True)
        
        embed.set_footer(text=f"User ID: {member.id}")
        
        member_count = len([m for m in guild.members if not m.bot])
        embed.add_field(name="Member Count", value=str(member_count), inline=True)
        
        return await log_channel.send(embed=embed)


class LogSettings:
    
    def __init__(self):
        self.log_channels = {}
    
    def set_log_channel(self, guild_id: int, channel_id: int):
        self.log_channels[guild_id] = channel_id
    
    def get_log_channel(self, guild_id: int) -> Optional[int]:
        return self.log_channels.get(guild_id)
    
    def remove_log_channel(self, guild_id: int):
        if guild_id in self.log_channels:
            del self.log_channels[guild_id]
