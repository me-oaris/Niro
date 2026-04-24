import sqlite3
import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import math

DB_PATH = "data/niro.db"

def ensure_db_dir():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

@dataclass
class GuildSettings:
    guild_id: int
    mod_role_id: Optional[int] = None
    admin_role_id: Optional[int] = None
    giveaway_role_id: Optional[int] = None
    leveling_enabled: bool = True
    xp_per_message: int = 10
    xp_cooldown: int = 60
    welcome_channel_id: Optional[int] = None
    welcome_message: str = "Welcome {user} to {server}!"
    log_channel_id: Optional[int] = None
    auto_role_ids: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GuildSettings':
        return cls(**data)

@dataclass
class UserLevel:
    user_id: int
    guild_id: int
    xp: int = 0
    level: int = 1
    messages: int = 0
    last_xp_gain: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserLevel':
        return cls(**data)

# User card color preferences
user_card_colors = {}

class Database:
    def __init__(self):
        ensure_db_dir()
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._load_user_card_colors()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Guild settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                mod_role_id INTEGER,
                admin_role_id INTEGER,
                giveaway_role_id INTEGER,
                leveling_enabled INTEGER DEFAULT 1,
                xp_per_message INTEGER DEFAULT 10,
                xp_cooldown INTEGER DEFAULT 60,
                welcome_channel_id INTEGER,
                welcome_message TEXT DEFAULT 'Welcome {user} to {server}!',
                log_channel_id INTEGER,
                auto_role_ids TEXT DEFAULT '[]',
                created_at TEXT
            )
        ''')
        
        # User levels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_levels (
                user_id INTEGER,
                guild_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                messages INTEGER DEFAULT 0,
                last_xp_gain TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        
        # Warnings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                reason TEXT,
                moderator_id INTEGER,
                created_at TEXT
            )
        ''')
        
        # User card colors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_card_colors (
                user_id INTEGER PRIMARY KEY,
                color TEXT DEFAULT 'default'
            )
        ''')
        
        # User messages by date table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_messages (
                user_id INTEGER,
                guild_id INTEGER,
                date TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, date)
            )
        ''')
        
        self.conn.commit()

    def _load_user_card_colors(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id, color FROM user_card_colors')
        rows = cursor.fetchall()
        for row in rows:
            user_card_colors[str(row['user_id'])] = row['color']
    
    def get_guild(self, guild_id: int) -> GuildSettings:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM guilds WHERE guild_id = ?', (guild_id,))
        row = cursor.fetchone()
        if row is None:
            created_at = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO guilds (guild_id, leveling_enabled, xp_per_message, xp_cooldown, welcome_message, auto_role_ids, created_at)
                VALUES (?, 1, 10, 60, 'Welcome {user} to {server}!', '[]', ?)
            ''', (guild_id, created_at))
            self.conn.commit()
            return GuildSettings(guild_id=guild_id, created_at=created_at)
        
        return GuildSettings(
            guild_id=row['guild_id'],
            mod_role_id=row['mod_role_id'],
            admin_role_id=row['admin_role_id'],
            giveaway_role_id=row['giveaway_role_id'],
            leveling_enabled=bool(row['leveling_enabled']),
            xp_per_message=row['xp_per_message'],
            xp_cooldown=row['xp_cooldown'],
            welcome_channel_id=row['welcome_channel_id'],
            welcome_message=row['welcome_message'],
            log_channel_id=row['log_channel_id'],
            auto_role_ids=json.loads(row['auto_role_ids']),
            created_at=row['created_at']
        )
    
    def update_guild(self, guild_id: int, **kwargs):
        guild = self.get_guild(guild_id)
        for key, value in kwargs.items():
            if hasattr(guild, key):
                setattr(guild, key, value)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE guilds SET
                mod_role_id = ?, admin_role_id = ?, giveaway_role_id = ?, leveling_enabled = ?,
                xp_per_message = ?, xp_cooldown = ?, welcome_channel_id = ?, welcome_message = ?,
                log_channel_id = ?, auto_role_ids = ?
            WHERE guild_id = ?
        ''', (
            guild.mod_role_id, guild.admin_role_id, guild.giveaway_role_id, int(guild.leveling_enabled),
            guild.xp_per_message, guild.xp_cooldown, guild.welcome_channel_id, guild.welcome_message,
            guild.log_channel_id, json.dumps(guild.auto_role_ids), guild_id
        ))
        self.conn.commit()
    
    def get_user_level(self, guild_id: int, user_id: int) -> UserLevel:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_levels WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
        row = cursor.fetchone()
        if row is None:
            cursor.execute('INSERT INTO user_levels (user_id, guild_id, xp, level, messages) VALUES (?, ?, 0, 1, 0)', (user_id, guild_id))
            self.conn.commit()
            return UserLevel(user_id=user_id, guild_id=guild_id)
        
        return UserLevel(user_id=row['user_id'], guild_id=row['guild_id'], xp=row['xp'], level=row['level'], messages=row['messages'], last_xp_gain=row['last_xp_gain'])
    
    def add_xp(self, guild_id: int, user_id: int, xp: int) -> tuple:
        user_level = self.get_user_level(guild_id, user_id)
        old_level = user_level.level
        user_level.xp += xp
        user_level.messages += 1
        user_level.last_xp_gain = datetime.now().isoformat()
        new_level = self._calculate_level(user_level.xp)
        user_level.level = new_level
        
        cursor = self.conn.cursor()
        cursor.execute('UPDATE user_levels SET xp = ?, level = ?, messages = ?, last_xp_gain = ? WHERE user_id = ? AND guild_id = ?', (user_level.xp, user_level.level, user_level.messages, user_level.last_xp_gain, user_id, guild_id))
        self.conn.commit()
        return xp, new_level
    
    def _calculate_level(self, xp: int) -> int:
        return max(1, int(math.sqrt(xp / 100)) + 1)
    
    def get_xp_for_level(self, level: int) -> int:
        return (level - 1) ** 2 * 100
    
    def get_level_progress(self, guild_id: int, user_id: int) -> dict:
        user_level = self.get_user_level(guild_id, user_id)
        current_level_xp = self.get_xp_for_level(user_level.level)
        next_level_xp = self.get_xp_for_level(user_level.level + 1)
        progress = (user_level.xp - current_level_xp) / max(1, (next_level_xp - current_level_xp)) * 100
        return {"level": user_level.level, "xp": user_level.xp, "current_level_xp": current_level_xp, "next_level_xp": next_level_xp, "xp_needed": next_level_xp - user_level.xp, "progress": progress, "messages": user_level.messages}
    
    def get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id, xp, level, messages FROM user_levels WHERE guild_id = ? ORDER BY xp DESC LIMIT ?', (guild_id, limit))
        rows = cursor.fetchall()
        return [{"user_id": row['user_id'], "xp": row['xp'], "level": row['level'], "messages": row['messages']} for row in rows]
    
    def add_warning(self, guild_id: int, user_id: int, reason: str, moderator_id: int) -> int:
        cursor = self.conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute('INSERT INTO warnings (guild_id, user_id, reason, moderator_id, created_at) VALUES (?, ?, ?, ?, ?)', (guild_id, user_id, reason, moderator_id, created_at))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_warnings(self, guild_id: int, user_id: int) -> list:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC', (guild_id, user_id))
        rows = cursor.fetchall()
        return [{"id": row['id'], "user_id": row['user_id'], "reason": row['reason'], "moderator_id": row['moderator_id'], "created_at": row['created_at']} for row in rows]
    
    def clear_warnings(self, guild_id: int, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM warnings WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
        self.conn.commit()
        
    def remove_warning(self, guild_id: int, warn_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM warnings WHERE guild_id = ? AND id = ?', (guild_id, warn_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_user_card_color(self, user_id: int) -> str:
        return user_card_colors.get(str(user_id), "default")
    
    def set_user_card_color(self, user_id: int, color: str):
        user_card_colors[str(user_id)] = color
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO user_card_colors (user_id, color) VALUES (?, ?)', (user_id, color))
        self.conn.commit()
    
    def add_message(self, guild_id: int, user_id: int):
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO user_messages (user_id, guild_id, date, count) VALUES (?, ?, ?, 1) ON CONFLICT(user_id, guild_id, date) DO UPDATE SET count = count + 1', (user_id, guild_id, today))
        self.conn.commit()
    
    def get_message_stats(self, guild_id: int, user_id: int) -> dict:
        cursor = self.conn.cursor()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        month_start = now.replace(day=1).strftime("%Y-%m-%d")
        
        cursor.execute('SELECT count FROM user_messages WHERE user_id = ? AND guild_id = ? AND date = ?', (user_id, guild_id, today))
        row = cursor.fetchone()
        today_count = row['count'] if row else 0
        
        cursor.execute('SELECT SUM(count) as total FROM user_messages WHERE user_id = ? AND guild_id = ? AND date >= ?', (user_id, guild_id, week_start))
        row = cursor.fetchone()
        week_count = row['total'] if row and row['total'] else 0
        
        cursor.execute('SELECT SUM(count) as total FROM user_messages WHERE user_id = ? AND guild_id = ? AND date >= ?', (user_id, guild_id, month_start))
        row = cursor.fetchone()
        month_count = row['total'] if row and row['total'] else 0
        
        return {"today": today_count, "week": week_count, "month": month_count}

db = Database()
