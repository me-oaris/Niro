import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from typing import Optional
import sys
import os
import random
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Components import EmbedComponent
from Modules.database import db
from .events import active_giveaways

class GiveawayInteractiveView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.message_id = None
        
        self.btn_enter = ui.Button(
            style=discord.ButtonStyle.blurple,
            emoji="🎉",
            label="0"
        )
        self.btn_enter.callback = self.on_enter
        
        self.btn_participants = ui.Button(
            label="Participants",
            style=discord.ButtonStyle.secondary,
            emoji="👥"
        )
        self.btn_participants.callback = self.on_participants

    async def on_enter(self, interaction: discord.Interaction):
        if not self.message_id or self.message_id not in active_giveaways:
            await interaction.response.send_message("This giveaway has ended or is invalid.", ephemeral=True)
            return
            
        giveaway = active_giveaways[self.message_id]
        if giveaway.get("ended"):
            await interaction.response.send_message("This giveaway has already ended.", ephemeral=True)
            return
            
        user = interaction.user
        
        bypass_role_id = giveaway.get("bypass_role")
        bypassed = bypass_role_id and bypass_role_id in [r.id for r in user.roles]
        
        if interaction.user.id in giveaway["entries"]:
            giveaway["entries"].remove(interaction.user.id)
            await interaction.response.send_message("You have left the giveaway.", ephemeral=True)
        else:
            if not bypassed:
                missing = []
                req_role = giveaway.get("required_role")
                if req_role and req_role not in [r.id for r in user.roles]:
                    missing.append(f"Role: <@&{req_role}>")
                    
                req_lvl = giveaway.get("required_level")
                if req_lvl:
                    user_level = db.get_user_level(interaction.guild.id, user.id)
                    if user_level.level < req_lvl:
                        missing.append(f"Level: **{req_lvl}** (You are {user_level.level})")
                
                req_total_msgs = giveaway.get("required_total_messages")
                if req_total_msgs:
                    user_level = db.get_user_level(interaction.guild.id, user.id)
                    if user_level.messages < req_total_msgs:
                        missing.append(f"Total Msgs: **{req_total_msgs}** (You have {user_level.messages})")
                
                req_daily = giveaway.get("required_daily_messages")
                req_weekly = giveaway.get("required_weekly_messages")
                req_monthly = giveaway.get("required_monthly_messages")
                if req_daily or req_weekly or req_monthly:
                    missing.append(f"Daily/Weekly/Monthly message requirements are not fully met.")
                
                if missing:
                    await interaction.response.send_message(f"❌ You do not meet the requirements to enter:\n" + "\n".join(missing), ephemeral=True)
                    return
                    
            giveaway["entries"].append(interaction.user.id)
            await interaction.response.send_message("You have successfully entered the giveaway!", ephemeral=True)
            
        self.btn_enter.label = str(len(giveaway["entries"]))
        await interaction.message.edit(view=self)

    async def on_participants(self, interaction: discord.Interaction):
        if not self.message_id or self.message_id not in active_giveaways:
            await interaction.response.send_message("This giveaway has ended or is invalid.", ephemeral=True)
            return
            
        giveaway = active_giveaways[self.message_id]
        entries = giveaway["entries"]
        if not entries:
            await interaction.response.send_message("No participants yet.", ephemeral=True)
            return
            
        parts = [f"<@{user_id}>" for user_id in entries[:50]]
        desc = "\n".join(parts)
        if len(entries) > 50:
            desc += f"\n...and {len(entries) - 50} more"
            
        embed = discord.Embed(
            title="Giveaway Participants",
            description=desc,
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GiveawayPrizeModal(ui.Modal, title="Set Giveaway Prize"):
    prize = ui.TextInput(label="Prize Name", placeholder="e.g., Discord Nitro", min_length=1, max_length=100)
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        
    async def on_submit(self, interaction: discord.Interaction):
        self.view.giveaway_data["prize"] = self.prize.value
        self.view._build_container()
        await interaction.response.edit_message(view=self.view)

class GiveawayWinnersModal(ui.Modal, title="Set Winners"):
    winners = ui.TextInput(label="Number of Winners", placeholder="e.g., 1 (Max: 10)", min_length=1, max_length=2)
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = int(self.winners.value)
            if 1 <= num <= 10:
                self.view.giveaway_data["winners"] = num
                self.view._build_container()
                await interaction.response.edit_message(view=self.view)
            else:
                await interaction.response.send_message("Winners must be between 1 and 10.", ephemeral=True)
        except:
            await interaction.response.send_message("Invalid number provided.", ephemeral=True)

class GiveawayDurationModal(ui.Modal, title="Set Duration"):
    duration = ui.TextInput(label="Duration", placeholder="e.g., 1h, 30m, 7d", min_length=2, max_length=10)
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        
    async def on_submit(self, interaction: discord.Interaction):
        duration_str = self.duration.value.lower().strip()
        seconds = 0
        if duration_str.endswith('d'): seconds = int(duration_str[:-1]) * 86400
        elif duration_str.endswith('h'): seconds = int(duration_str[:-1]) * 3600
        elif duration_str.endswith('m'): seconds = int(duration_str[:-1]) * 60
        elif duration_str.endswith('s'): seconds = int(duration_str[:-1])
        
        if seconds > 0:
            self.view.giveaway_data["duration"] = seconds
            self.view._build_container()
            await interaction.response.edit_message(view=self.view)
        else:
            await interaction.response.send_message("Invalid duration. Use format: 10m, 2h, 1d", ephemeral=True)


class GiveawaySetupView(ui.LayoutView):
    def __init__(self, guild_id: int, user_id: int, bot):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.user_id = user_id
        self.bot = bot
        self.giveaway_data = {
            "prize": "Enter prize here",
            "winners": 1,
            "duration": 86400,
            "extra_entries_enabled": False,
            "extra_entries_roles": [],
            "emoji": "🎉"
        }
        
        self._build_container()
    
    def _format_duration(self, seconds: int) -> str:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        mins = (seconds % 3600) // 60
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0:
            parts.append(f"{mins}m")
        return " ".join(parts) or "0m"
    
    def _build_container(self):
        self.clear_items()
        self.btn_prize = ui.Button(
            label="Set Prize",
            style=discord.ButtonStyle.blurple,
            emoji="🎁",
            custom_id="set_prize"
        )
        self.btn_prize.callback = self._set_prize
        
        self.btn_winners = ui.Button(
            label="Set Winners",
            style=discord.ButtonStyle.blurple,
            emoji="👥",
            custom_id="set_winners"
        )
        self.btn_winners.callback = self._set_winners
        
        self.btn_duration = ui.Button(
            label="Set Duration",
            style=discord.ButtonStyle.blurple,
            emoji="⏰",
            custom_id="set_duration"
        )
        self.btn_duration.callback = self._set_duration
        
        self.btn_start = ui.Button(
            label="Start Giveaway",
            style=discord.ButtonStyle.green,
            emoji="▶️",
            custom_id="start_giveaway"
        )
        self.btn_start.callback = self._start_giveaway
        
        self.btn_cancel = ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.red,
            emoji="✖️",
            custom_id="cancel"
        )
        self.btn_cancel.callback = self._cancel
        
        self.container = ui.Container(
            ui.TextDisplay(
                f"## 🎉 Giveaway Setup\n\n"
                f"Configure your giveaway:\n\n"
                f"**🎁 Prize**: {self.giveaway_data['prize']}\n"
                f"**👥 Winners**: {self.giveaway_data['winners']}\n"
                f"**⏰ Duration**: {self._format_duration(self.giveaway_data['duration'])}"
            ),
            ui.ActionRow(self.btn_prize, self.btn_winners, self.btn_duration),
            ui.ActionRow(self.btn_start, self.btn_cancel),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your setup panel!", ephemeral=True)
            return False
        return True
    
    async def _set_prize(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GiveawayPrizeModal(self))
    
    async def _set_winners(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GiveawayWinnersModal(self))
    
    async def _set_duration(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GiveawayDurationModal(self))
    
    async def _start_giveaway(self, interaction: discord.Interaction):
        channel = interaction.channel
        end_time = datetime.now() + timedelta(seconds=self.giveaway_data["duration"])
        
        desc = (
            f"Click {self.giveaway_data['emoji']} button to enter!\n"
            f"Winners: **{self.giveaway_data['winners']}**\n"
            f"Ends: <t:{int(end_time.timestamp())}:R>\n\n"
            f"Ends at • <t:{int(end_time.timestamp())}:f>\n"
            f"**Hosted by {interaction.user.name}**"
        )
        
        view = GiveawayInteractiveView()
        view.btn_enter.emoji = self.giveaway_data["emoji"]
        
        container = ui.Container(
            ui.TextDisplay(f"## **{self.giveaway_data['prize']}**\n{desc}"),
            ui.ActionRow(view.btn_enter, view.btn_participants),
            accent_color=discord.Color.blurple()
        )
        view.add_item(container)
        
        msg = await channel.send(view=view)
        
        view.message_id = msg.id
        
        active_giveaways[msg.id] = {
            "prize": self.giveaway_data["prize"],
            "winners": self.giveaway_data["winners"],
            "end_time": end_time,
            "emoji": self.giveaway_data["emoji"],
            "host": interaction.user.id,
            "guild_id": interaction.guild.id,
            "extra_entries_enabled": False,
            "extra_entries_roles": [],
            "entries": []
        }
        
        await interaction.message.delete()
        
        asyncio.create_task(self._end_giveaway(msg.id, channel, self.bot))
    
    async def _cancel(self, interaction: discord.Interaction):
        await interaction.response.send_message("Cancelled.", ephemeral=True)
        await interaction.message.delete()
    
    async def _refresh_message(self, interaction: discord.Interaction):
        try:
            self._build_container()
            await interaction.message.edit(view=self)
        except:
            pass
    
    async def _end_giveaway(self, message_id: int, channel: discord.TextChannel, bot):
        await asyncio.sleep(3)
        if message_id not in active_giveaways: return
        
        giveaway = active_giveaways[message_id]
        wait_time = (giveaway["end_time"] - datetime.now()).total_seconds()
        if wait_time > 0: await asyncio.sleep(wait_time)
        
        if message_id not in active_giveaways or giveaway.get("ended"): return
        giveaway["ended"] = True
        
        try:
            msg = await channel.fetch_message(message_id)
        except: return
        
        entries = giveaway["entries"]
        winners = random.sample(entries, min(len(entries), giveaway["winners"]))
        host_mention = f"<@{giveaway['host']}>"
        
        end_color = discord.Color.from_str("#2f3136")
        if winners:
            winner_mentions = ", ".join(f"<@{w}>" for w in winners)
            
            try:
                host_user = bot.get_user(giveaway['host']) or await bot.fetch_user(giveaway['host'])
                host_avatar = host_user.display_avatar.url
            except:
                host_avatar = None
                
            cong_embed = discord.Embed(
                title=f"🎉 Giveaway Winner Announcement",
                description=f"Congratulations to {winner_mentions}! You won the giveaway for **{giveaway['prize']}**!\n\n**Hosted by:** {host_mention}\n**Reroll Command:** `/geroll {message_id}`",
                color=discord.Color.from_str("#4da8da")
            )
            
            view = GiveawayInteractiveView()
            view.message_id = message_id
            view.btn_enter.label = str(len(entries))
            view.btn_enter.disabled = True
            view.btn_participants.disabled = True
            
            container_items = [
                ui.Section(
                    f"## 🎊 Giveaway Ended",
                    f"The giveaway for **{giveaway['prize']}** has concluded.\n\n"
                    f"**Winner:** {winner_mentions}\n"
                    f"**Hosted by:** {host_mention}",
                    accessory=ui.Thumbnail(giveaway.get("thumbnail_url") or host_avatar)
                )
            ]
            
            if giveaway.get("image_url"):
                container_items.append(ui.MediaSlot(url=giveaway["image_url"]))
                
            container_items.extend([
                ui.Separator(),
                ui.TextDisplay(f"*Ended at* • <t:{int(datetime.now().timestamp())}:f>"),
                ui.ActionRow(view.btn_enter, view.btn_participants)
            ])
            
            container = ui.Container(*container_items, accent_color=end_color)
            view.add_item(container)
            
            await msg.edit(view=view)
            announcement = await channel.send(content=f"Congratulations! 🎉 {winner_mentions}", embed=cong_embed)
            giveaway["announcement_id"] = announcement.id
            
            for winner_id in winners:
                try:
                    winner_user = bot.get_user(winner_id) or await bot.fetch_user(winner_id)
                    dm_embed = discord.Embed(
                        title="🎉 You won a giveaway!",
                        description=f"Congratulations! You won **{giveaway['prize']}** in **{channel.guild.name}**!",
                        color=discord.Color.green()
                    )
                    dm_view = ui.View()
                    dm_view.add_item(ui.Button(label="View Giveaway", url=msg.jump_url))
                    await winner_user.send(embed=dm_embed, view=dm_view)
                except: pass
        else:
            view = GiveawayInteractiveView()
            view.btn_enter.disabled = True
            view.btn_participants.disabled = True
            
            try:
                host_user = bot.get_user(giveaway['host']) or await bot.fetch_user(giveaway['host'])
                host_avatar = host_user.display_avatar.url
            except:
                host_avatar = None
                
            container_items = [
                ui.Section(
                    f"## 🎊 Giveaway Ended",
                    f"The giveaway for **{giveaway['prize']}** has concluded.\n\n"
                    f"**Winner:** None (Not enough entries)\n"
                    f"**Hosted by:** {host_mention}",
                    accessory=ui.Thumbnail(giveaway.get("thumbnail_url") or host_avatar)
                )
            ]
            
            if giveaway.get("image_url"):
                container_items.append(ui.MediaSlot(url=giveaway["image_url"]))
                
            container_items.extend([
                ui.Separator(),
                ui.TextDisplay(f"*Ended at* • <t:{int(datetime.now().timestamp())}:f>"),
                ui.ActionRow(view.btn_enter, view.btn_participants)
            ])
            
            container = ui.Container(*container_items, accent_color=end_color)
            view.add_item(container)
            await msg.edit(view=view)
            await channel.send(f"Giveaway ended! No valid entries for **{giveaway['prize']}**")


class GiveawayCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def check_permissions(self, interaction: discord.Interaction) -> str:
        guild = interaction.guild
        actor = interaction.user
        
        if not guild:
            return None
        
        if actor.id == guild.owner_id:
            return None
        
        settings = db.get_guild(guild.id)
        if settings.giveaway_role_id:
            if settings.giveaway_role_id in [role.id for role in actor.roles]:
                return None
        
        return "No permission."
    
    @app_commands.command(name="giveaway", description="Start a giveaway")
    @app_commands.guild_only()
    async def giveaway_command(self, interaction: discord.Interaction):
        perm = await self.check_permissions(interaction)
        if perm:
            await interaction.response.send_message(embed=EmbedComponent.error("Permission Denied", perm), ephemeral=True)
            return
        
        view = GiveawaySetupView(interaction.guild.id, interaction.user.id, self.bot)
        await interaction.response.send_message(view=view)
    
    @app_commands.command(name="gcreate", description="Advanced create giveaway")
    @app_commands.describe(prize="Prize", duration="Duration (e.g., 1h)", winners="Number of winners",
                           channel="Channel to host the giveaway in", host="User hosting the giveaway",
                           image="Image to display in the embed", thumbnail="Thumbnail for the embed",
                           required_role="Role required to enter", required_level="Level required to enter",
                           required_daily_messages="Daily messages required", required_weekly_messages="Weekly messages required",
                           required_monthly_messages="Monthly messages required", required_total_messages="Total messages required",
                           requirement_bypass_role="Role that bypasses all requirements", color="Embed color hex code (e.g., #ff0000)",
                           end_color="Embed color when ended", other_options="Other custom settings")
    @app_commands.guild_only()
    async def gcreate_command(
        self, interaction: discord.Interaction, 
        prize: str, duration: str = "24h", winners: int = 1,
        channel: discord.TextChannel = None, host: discord.Member = None,
        image: discord.Attachment = None, thumbnail: discord.Attachment = None,
        required_role: discord.Role = None, required_level: int = None,
        required_daily_messages: int = None, required_weekly_messages: int = None,
        required_monthly_messages: int = None, required_total_messages: int = None,
        requirement_bypass_role: discord.Role = None, color: str = None,
        end_color: str = None, other_options: str = None
    ):
        perm = await self.check_permissions(interaction)
        if perm:
            await interaction.response.send_message(embed=EmbedComponent.error("Permission Denied", perm), ephemeral=True)
            return
        
        duration_str = duration.lower().strip()
        seconds = 0
        if duration_str.endswith('d'):
            seconds = int(duration_str[:-1]) * 86400
        elif duration_str.endswith('h'):
            seconds = int(duration_str[:-1]) * 3600
        elif duration_str.endswith('m'):
            seconds = int(duration_str[:-1]) * 60
        elif duration_str.endswith('s'):
            seconds = int(duration_str[:-1])
        
        if seconds == 0 or not 1 <= winners <= 100:
            await interaction.response.send_message(embed=EmbedComponent.error("Invalid", "Invalid duration or winners"), ephemeral=True)
            return
            
        target_channel = channel or interaction.channel
        giveaway_host = host or interaction.user
        
        embed_color = discord.Color.blurple()
        if color:
            try:
                if color.startswith('#'): color = color[1:]
                embed_color = discord.Color(int(color, 16))
            except: pass
        
        end_time = datetime.now() + timedelta(seconds=seconds)
        
        desc = (
            f"Click 🎉 button to enter!\n"
            f"Winners: **{winners}**\n"
            f"Ends: <t:{int(end_time.timestamp())}:R>\n\n"
            f"Ends at • <t:{int(end_time.timestamp())}:f>\n"
            f"**Hosted by {giveaway_host.name}**"
        )
        
        reqs = []
        if required_role: reqs.append(f"• Role: {required_role.mention}")
        if required_level: reqs.append(f"• Level: **{required_level}**")
        if required_daily_messages: reqs.append(f"• Daily Msgs: **{required_daily_messages}**")
        if required_weekly_messages: reqs.append(f"• Weekly Msgs: **{required_weekly_messages}**")
        if required_monthly_messages: reqs.append(f"• Monthly Msgs: **{required_monthly_messages}**")
        if required_total_messages: reqs.append(f"• Total Msgs: **{required_total_messages}**")
        
        if reqs:
            bypass_text = f"\n*Bypass Requirement: {requirement_bypass_role.mention}*" if requirement_bypass_role else ""
            desc += f"\n\n**Requirements**\n" + "\n".join(reqs) + bypass_text
        
        view = GiveawayInteractiveView()
        
        container_components = [
            ui.TextDisplay(f"## **{prize}**\n{desc}")
        ]
        
        if image:
            container_components.append(ui.MediaGallery(discord.MediaGalleryItem(url=image.url)))
        if thumbnail and not image:
            container_components.append(ui.MediaGallery(discord.MediaGalleryItem(url=thumbnail.url)))
            
        container_components.append(ui.ActionRow(view.btn_enter, view.btn_participants))
        
        container = ui.Container(
            *container_components,
            accent_color=embed_color
        )
        view.add_item(container)
        
        msg = await target_channel.send(view=view)
        view.message_id = msg.id
        
        print(f"Creating giveaway {msg.id} in {target_channel.name}")
        
        active_giveaways[msg.id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_time,
            "emoji": "🎉",
            "host": giveaway_host.id,
            "guild_id": interaction.guild.id,
            "channel_id": target_channel.id,
            "image_url": image.url if image else None,
            "thumbnail_url": thumbnail.url if thumbnail else None,
            "required_role": required_role.id if required_role else None,
            "required_level": required_level,
            "required_daily_messages": required_daily_messages,
            "required_weekly_messages": required_weekly_messages,
            "required_monthly_messages": required_monthly_messages,
            "required_total_messages": required_total_messages,
            "bypass_role": requirement_bypass_role.id if requirement_bypass_role else None,
            "end_color": end_color,
            "entries": []
        }
        
        await interaction.response.send_message("Giveaway started!", ephemeral=True)
        
        asyncio.create_task(self._end_giveaway(msg.id, target_channel))
    
    async def _end_giveaway(self, message_id: int, channel: discord.TextChannel):
        await asyncio.sleep(3)
        
        if message_id not in active_giveaways:
            return
        
        giveaway = active_giveaways[message_id]
        wait_time = (giveaway["end_time"] - datetime.now()).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        if message_id not in active_giveaways:
            return
            
        giveaway = active_giveaways[message_id]
        if giveaway.get("ended"):
            return
            
        giveaway["ended"] = True
        
        try:
            msg = await channel.fetch_message(message_id)
        except:
            giveaway["ended"] = True
            return
        
        entries = giveaway["entries"]
        winners = random.sample(entries, min(len(entries), giveaway["winners"])) if entries else []
            
        host_id = giveaway.get("host")
        host_mention = f"<@{host_id}>" if host_id else "Unknown"
        
        end_color = discord.Color.from_str("#2f3136")
        if giveaway.get("end_color"):
            try:
                c = giveaway["end_color"]
                if c.startswith('#'): c = c[1:]
                end_color = discord.Color(int(c, 16))
            except: pass
            
        winners = random.sample(entries, min(len(entries), giveaway["winners"])) if entries else []
            
        if winners:
            winner_mentions = ", ".join(f"<@{w}>" for w in winners)
            
            try:
                host_user = self.bot.get_user(giveaway['host']) or await self.bot.fetch_user(giveaway['host'])
                host_avatar = host_user.display_avatar.url
            except:
                host_avatar = None
                
            cong_embed = discord.Embed(
                title=f"🎉 Giveaway Winner!!",
                description=f"Congratulations to {winner_mentions}! You won the giveaway for **{giveaway['prize']}**!\n\n**Hosted by:** {host_mention}\n**Reroll Command:** `/geroll {message_id}`",
                color=discord.Color.from_str("#4da8da")
            )
            
            view = GiveawayInteractiveView()
            view.message_id = message_id
            view.btn_enter.label = str(len(entries))
            view.btn_enter.disabled = True
            view.btn_participants.disabled = True
            
            container_items = [
                ui.Section(
                    f"## 🎊 Giveaway Ended",
                    f"The giveaway for **{giveaway['prize']}** has concluded.\n\n"
                    f"**Winner:** {winner_mentions}\n"
                    f"**Hosted by:** {host_mention}",
                    accessory=ui.Thumbnail(giveaway.get("thumbnail_url") or host_avatar)
                )
            ]
            
            if giveaway.get("image_url"):
                container_items.append(ui.MediaSlot(url=giveaway["image_url"]))
                
            container_items.extend([
                ui.Separator(),
                ui.TextDisplay(f"*Ended at* • <t:{int(datetime.now().timestamp())}:f>"),
                ui.ActionRow(view.btn_enter, view.btn_participants)
            ])
            
            container = ui.Container(*container_items, accent_color=end_color)
            view.add_item(container)
            
            await msg.edit(view=view)
            announcement = await channel.send(content=f"Congratulations! 🎉 {winner_mentions}", embed=cong_embed)
            giveaway["announcement_id"] = announcement.id
            
            for winner_id in winners:
                try:
                    winner_user = self.bot.get_user(winner_id) or await self.bot.fetch_user(winner_id)
                    dm_embed = discord.Embed(
                        title="🎉 You won a giveaway!",
                        description=f"Congratulations! You won **{giveaway['prize']}** in **{channel.guild.name}**!",
                        color=discord.Color.green()
                    )
                    
                    dm_view = ui.View()
                    dm_view.add_item(ui.Button(label="View Giveaway", url=msg.jump_url))
                    
                    await winner_user.send(embed=dm_embed, view=dm_view)
                except:
                    pass
        else:
            view = GiveawayInteractiveView()
            view.message_id = message_id
            view.btn_enter.label = str(len(entries))
            view.btn_enter.disabled = True
            view.btn_participants.disabled = True
            
            try:
                host_user = self.bot.get_user(giveaway['host']) or await self.bot.fetch_user(giveaway['host'])
                host_avatar = host_user.display_avatar.url
            except:
                host_avatar = None
                
            container_items = [
                ui.Section(
                    f"## 🎊 Giveaway Ended",
                    f"The giveaway for **{giveaway['prize']}** has concluded.\n\n"
                    f"**Winner:** None (Not enough entries)\n"
                    f"**Hosted by:** {host_mention}",
                    accessory=ui.Thumbnail(giveaway.get("thumbnail_url") or host_avatar)
                )
            ]
            
            if giveaway.get("image_url"):
                container_items.append(ui.MediaSlot(url=giveaway["image_url"]))
                
            container_items.extend([
                ui.Separator(),
                ui.TextDisplay(f"*Ended at* • <t:{int(datetime.now().timestamp())}:f>"),
                ui.ActionRow(view.btn_enter, view.btn_participants)
            ])
            
            container = ui.Container(*container_items, accent_color=end_color)
            view.add_item(container)
            await msg.edit(view=view)
            await channel.send(f"Giveaway ended! No valid entries for **{giveaway['prize']}**")
    
    @app_commands.command(name="geroll", description="Reroll a giveaway")
    @app_commands.describe(message="The giveaway message ID or link (optional: defaults to latest ended)")
    @app_commands.guild_only()
    async def geroll_command(self, interaction: discord.Interaction, message: Optional[str] = None):
        perm = await self.check_permissions(interaction)
        if perm:
            await interaction.response.send_message(embed=EmbedComponent.error("Permission Denied", perm), ephemeral=True)
            return
        
        msg_id = None
        if message:
            try:
                if "discord.com/channels/" in message:
                    parts = message.split("/")
                    msg_id = int(parts[-1])
                else:
                    msg_id = int(message)
            except:
                await interaction.response.send_message(embed=EmbedComponent.error("Invalid", "Invalid message ID"), ephemeral=True)
                return
        else:
            ended_gws = [(mid, data) for mid, data in active_giveaways.items() if data.get("ended") and data.get("guild_id", interaction.guild.id) == interaction.guild.id]
            if not ended_gws:
                ended_gws = [(mid, data) for mid, data in active_giveaways.items() if data.get("ended")]
                
            if not ended_gws:
                await interaction.response.send_message(embed=EmbedComponent.error("Not Found", "No recently ended giveaways found in this server."), ephemeral=True)
                return
                
            ended_gws.sort(key=lambda x: x[1].get("end_time", datetime.min), reverse=True)
            msg_id = ended_gws[0][0]
        
        if msg_id not in active_giveaways:
            await interaction.response.send_message(embed=EmbedComponent.error("Not Found", "Giveaway not found or already ended"), ephemeral=True)
            return
        
        giveaway = active_giveaways[msg_id]
        if not giveaway.get("ended"):
            await interaction.response.send_message(embed=EmbedComponent.error("Error", "Giveaway has not ended yet!"), ephemeral=True)
            return
            
        entries = giveaway["entries"]
        
        if not entries:
            await interaction.response.send_message(embed=EmbedComponent.error("No Entries", "No entries to reroll from!"), ephemeral=True)
            return
        
        if len(entries) < giveaway["winners"]:
            winners = entries
        else:
            winners = random.sample(entries, giveaway["winners"])
        
        if winners:
            winner_mentions = ", ".join(f"<@{w}>" for w in winners)
            
            try:
                host_user = self.bot.get_user(giveaway['host']) or await self.bot.fetch_user(giveaway['host'])
                host_avatar = host_user.display_avatar.url
            except:
                host_avatar = None
                
            cong_embed = discord.Embed(
                title=f"🎉 Giveaway Winner Announcement",
                description=f"Congratulations to {winner_mentions}! You won the giveaway for **{giveaway['prize']}**!\n\n**Hosted by:** <@{giveaway['host']}>\n**Reroll Command:** `/geroll {msg_id}`",
                color=discord.Color.from_str("#4da8da")
            )
            
            reply_to = None
            if giveaway.get("announcement_id"):
                try:
                    reply_to = await interaction.channel.fetch_message(giveaway["announcement_id"])
                except: pass
            
            if reply_to:
                announcement = await reply_to.reply(content=f"🎉 New winner(s)! {winner_mentions}", embed=cong_embed)
            else:
                announcement = await interaction.channel.send(content=f"🎉 New winner(s)! {winner_mentions}", embed=cong_embed)
                
            giveaway["announcement_id"] = announcement.id
            await interaction.response.send_message("Giveaway successfully rerolled!", ephemeral=True)
            
            try:
                gw_msg = await interaction.channel.fetch_message(msg_id)
                jump_url = gw_msg.jump_url
            except:
                jump_url = None
                
            for winner_id in winners:
                try:
                    winner_user = self.bot.get_user(winner_id) or await self.bot.fetch_user(winner_id)
                    dm_embed = discord.Embed(
                        title="🎉 You won a giveaway!",
                        description=f"Congratulations! You won **{giveaway['prize']}** in **{interaction.guild.name}**!",
                        color=discord.Color.green()
                    )
                    if jump_url:
                        dm_view = ui.View()
                        dm_view.add_item(ui.Button(label="View Giveaway", url=jump_url))
                        await winner_user.send(embed=dm_embed, view=dm_view)
                    else:
                        await winner_user.send(embed=dm_embed)
                except: pass
        else:
            await interaction.response.send_message(embed=EmbedComponent.error("Error", "Could not pick winners"), ephemeral=True)
    
    @app_commands.command(name="gend", description="End a giveaway early")
    @app_commands.describe(message="The giveaway message ID or link")
    @app_commands.guild_only()
    async def gend_command(self, interaction: discord.Interaction, message: str):
        perm = await self.check_permissions(interaction)
        if perm:
            await interaction.response.send_message(embed=EmbedComponent.error("Permission Denied", perm), ephemeral=True)
            return
        
        try:
            if "discord.com/channels/" in message:
                parts = message.split("/")
                msg_id = int(parts[-1])
            else:
                msg_id = int(message)
        except:
            await interaction.response.send_message(embed=EmbedComponent.error("Invalid", "Invalid message ID"), ephemeral=True)
            return
        
        if msg_id not in active_giveaways:
            await interaction.response.send_message(embed=EmbedComponent.error("Not Found", "Giveaway not found"), ephemeral=True)
            return
        
        giveaway = active_giveaways[msg_id]
        if giveaway.get("ended"):
            await interaction.response.send_message(embed=EmbedComponent.error("Error", "Giveaway has already ended!"), ephemeral=True)
            return
            
        giveaway["end_time"] = datetime.now()
        await interaction.response.send_message("Ending giveaway...", ephemeral=True)
        
        channel_id = giveaway.get("channel_id", interaction.channel.id)
        try:
            channel = interaction.guild.get_channel(channel_id) or await interaction.guild.fetch_channel(channel_id)
            await self._end_giveaway(msg_id, channel)
        except:
            pass


async def setup(bot):
    await bot.add_cog(GiveawayCommands(bot))