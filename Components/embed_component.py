import discord
import io
import math
import aiohttp
from typing import List, Optional


class EmbedComponent:
    DEFAULT_COLOR = discord.Color.from_rgb(88, 101, 242)  # Blurple
    SUCCESS_COLOR = discord.Color.from_rgb(35, 209, 96)   # Green
    ERROR_COLOR = discord.Color.from_rgb(240, 71, 71)      # Red
    WARNING_COLOR = discord.Color.from_rgb(255, 166, 58)   # Orange
    INFO_COLOR = discord.Color.from_rgb(88, 101, 242)      # Blurple
    LEVEL_COLOR = discord.Color.from_rgb(88, 101, 242)    # Blurple
    
    @staticmethod
    def create(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: discord.Color = None,
        footer: Optional[str] = None,
        footer_icon: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        author: Optional[str] = None,
        author_icon: Optional[str] = None,
        fields: Optional[List[tuple]] = None,
        timestamp: bool = False,
        url: Optional[str] = None
    ) -> discord.Embed:

        embed = discord.Embed(
            title=title,
            description=description,
            color=color or EmbedComponent.DEFAULT_COLOR,
            url=url
        )
        
        if footer:
            embed.set_footer(text=footer, icon_url=footer_icon)
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if image:
            embed.set_image(url=image)
        
        if author:
            embed.set_author(name=author, icon_url=author_icon)
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        
        if timestamp:
            import datetime
            embed.timestamp = datetime.datetime.now()
        
        return embed
    
    @staticmethod
    def success(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"✅ {title}",
            description=description,
            color=EmbedComponent.SUCCESS_COLOR,
            **kwargs
        )
    
    @staticmethod
    def error(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"❌ {title}",
            description=description,
            color=EmbedComponent.ERROR_COLOR,
            **kwargs
        )
    
    @staticmethod
    def warning(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"⚠️ {title}",
            description=description,
            color=EmbedComponent.WARNING_COLOR,
            **kwargs
        )
    
    @staticmethod
    def info(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"ℹ️ {title}",
            description=description,
            color=EmbedComponent.INFO_COLOR,
            **kwargs
        )
    
    @staticmethod
    def level(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"⭐ {title}",
            description=description,
            color=EmbedComponent.LEVEL_COLOR,
            **kwargs
        )
    
    @staticmethod
    def mod(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"🛡️ {title}",
            description=description,
            color=EmbedComponent.DEFAULT_COLOR,
            **kwargs
        )
    
    @staticmethod
    def settings(title: str, description: str, **kwargs) -> discord.Embed:
        return EmbedComponent.create(
            title=f"⚙️ {title}",
            description=description,
            color=EmbedComponent.INFO_COLOR,
            **kwargs
        )
    
    @staticmethod
    def pagination_embed(
        items: List[str],
        title: str,
        items_per_page: int = 10,
        number_items: bool = True
    ) -> List[discord.Embed]:
        embeds = []
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        
        for page in range(total_pages):
            start = page * items_per_page
            end = start + items_per_page
            page_items = items[start:end]
            
            content = "\n".join(
                f"{i+1}. {item}" if number_items else item 
                for i, item in enumerate(page_items)
            )
            
            embed = discord.Embed(
                title=f"{title} (Page {page + 1}/{total_pages})",
                description=content or "No items",
                color=EmbedComponent.DEFAULT_COLOR
            )
            embeds.append(embed)
        
        return embeds
    
    @staticmethod
    async def create_level_card(
        user: discord.User | discord.Member,
        level: int,
        xp: int,
        xp_needed: int,
        progress: float,
        rank: int = None,
        background_color: tuple = (30, 30, 35),
        accent_color: tuple = (88, 101, 242),
        show_shine: bool = True
    ) -> discord.File:
        from PIL import Image, ImageDraw, ImageFont
        import aiohttp
        import io
        from urllib.request import urlopen

        async def download_avatar(avatar_url: str, size: int = 120) -> Image.Image:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(avatar_url)) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            img = Image.open(io.BytesIO(data)).convert('RGBA')
                            min_dim = min(img.size)
                            left = (img.width - min_dim) // 2
                            top = (img.height - min_dim) // 2
                            img = img.crop((left, top, left + min_dim, top + min_dim))
                            img = img.resize((size, size), Image.Resampling.LANCZOS)
                            return img
                return None
            except:
                return None

        WIDTH = 900
        HEIGHT = 280
        
        BG_TOP = accent_color
        BG_BOTTOM = background_color
        ACCENT = accent_color
        ACCENT_LIGHT = tuple(min(c + 60, 255) for c in accent_color)
        ACCENT_DARK = tuple(max(c - 60, 0) for c in accent_color)
        
        TEXT_PRIMARY = (255, 255, 255)
        TEXT_SECONDARY = (200, 200, 210)
        PROGRESS_BG = (40, 40, 45)
        RANK_GOLD = (255, 166, 58)
        BORDER_WHITE = (255, 255, 255)
        SHADOW_COLOR = (0, 0, 0)
        
        img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # ===== BACKGROUND GRADIENT =====
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
            g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
            b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
        
        # Add subtle vignette effect (darker edges)
        for x in range(WIDTH):
            for y in range(HEIGHT):
                dist_x = min(x, WIDTH - x) / (WIDTH / 2)
                dist_y = min(y, HEIGHT - y) / (HEIGHT / 2)
                dist = (dist_x + dist_y) / 2
                if dist < 1:
                    shade = int(255 * (1 - (1 - dist) * 0.15))
        
        # Shadow for card depth
        draw.rounded_rectangle([12, 12, WIDTH - 8, HEIGHT - 8], radius=25, outline=SHADOW_COLOR, width=1, fill=None)
        
        # Main border - GLOW EFFECT
        draw.rounded_rectangle([8, 8, WIDTH - 8, HEIGHT - 8], radius=25, outline=ACCENT, width=3)
        
        # Subtle inner border highlight
        draw.rounded_rectangle([10, 10, WIDTH - 10, HEIGHT - 10], radius=24, outline=ACCENT_LIGHT, width=1)
        
        # ===== FONTS =====
        try:
            font_xl = ImageFont.truetype("arial.ttf", 60)
            font_lg = ImageFont.truetype("arial.ttf", 40)
            font_md = ImageFont.truetype("arial.ttf", 26)
            font_sm = ImageFont.truetype("arial.ttf", 18)
            font_xs = ImageFont.truetype("arial.ttf", 15)
        except:
            font_xl = ImageFont.load_default()
            font_lg = font_xl
            font_md = font_xl
            font_sm = font_xl
            font_xs = font_xl
        
        # ===== AVATAR WITH GLOW =====
        avatar_size = 120
        avatar_x, avatar_y = 45, 60
        
        # Avatar glow (larger circle behind)
        glow_size = avatar_size + 12
        glow_x, glow_y = avatar_x - 6, avatar_y - 6
        draw.ellipse([glow_x, glow_y, glow_x + glow_size, glow_y + glow_size], 
                     fill=tuple(int(c * 0.3) for c in ACCENT) + (80,))
        
        avatar_img = await download_avatar(user.display_avatar.url, avatar_size)
        username = user.name
        
        if avatar_img:
            mask = Image.new('L', (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size - 1, avatar_size - 1], fill=255)
            avatar_img.putalpha(mask)
            
            # Create a transparent base for the avatar and border
            border_img = Image.new('RGBA', (avatar_size + 10, avatar_size + 10), (0, 0, 0, 0))
            border_draw = ImageDraw.Draw(border_img)
            
            # Draw white border circle
            border_draw.ellipse([0, 0, avatar_size + 9, avatar_size + 9], fill=BORDER_WHITE)
            
            # Paste the circular avatar
            border_img.paste(avatar_img, (5, 5), avatar_img)
            
            img.paste(border_img, (avatar_x - 5, avatar_y - 5), border_img)
        else:
            # White border
            draw.ellipse([avatar_x - 5, avatar_y - 5, avatar_x + avatar_size + 5, avatar_y + avatar_size + 5], 
                         fill=BORDER_WHITE)
            
            # Avatar background
            draw.ellipse([avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size], fill=(110, 110, 130))
            
            if username:
                initial = username[0].upper()
                draw.text((avatar_x + 32, avatar_y + 25), initial, fill=TEXT_PRIMARY, font=font_xl)
        
        # ===== USERNAME =====
        draw.text((180, 68), username[:20], fill=TEXT_PRIMARY, font=font_lg)
        
        # ===== LEVEL BADGE WITH GLOW =====
        level_text = f"LVL {level}"
        level_bbox = draw.textbbox((0, 0), level_text, font=font_md)
        level_w = level_bbox[2] - level_bbox[0]
        level_h = level_bbox[3] - level_bbox[1]
        
        badge_x, badge_y = 180, 125
        badge_w, badge_h = level_w + 18, level_h + 10
        
        # Badge shadow
        draw.rounded_rectangle([badge_x + 2, badge_y + 2, badge_x + badge_w + 2, badge_y + badge_h + 2], 
                               radius=8, fill=(0, 0, 0, 40))
        
        # Badge background
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 
                               radius=8, fill=ACCENT)
        
        # Badge shine
        draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h // 2], 
                               radius=8, fill=ACCENT_LIGHT)
        
        draw.text((badge_x + 10, badge_y + 1), level_text, fill=TEXT_PRIMARY, font=font_md)
        
        # ===== RANK BADGE =====
        if rank:
            rank_text = f"#{rank}"
            rank_bbox = draw.textbbox((0, 0), rank_text, font=font_lg)
            rank_w = rank_bbox[2] - rank_bbox[0]
            
            rank_x = WIDTH - rank_w - 60
            rank_y = 55
            rank_w_total = rank_w + 35
            rank_h_total = 70
            
            # Rank shadow
            draw.rounded_rectangle([rank_x + 2, rank_y + 2, rank_x + rank_w_total + 2, rank_y + rank_h_total + 2], 
                                   radius=10, fill=(0, 0, 0, 60))
            
            # Rank background
            draw.rounded_rectangle([rank_x, rank_y, rank_x + rank_w_total, rank_y + rank_h_total], 
                                   radius=10, fill=RANK_GOLD)
            
            # Rank shine
            draw.rounded_rectangle([rank_x, rank_y, rank_x + rank_w_total, rank_y + rank_h_total // 2], 
                                   radius=10, fill=(255, 200, 100))
            
            draw.text((rank_x + 17, rank_y + 12), rank_text, fill=(50, 30, 0), font=font_lg)
        
        # ===== PROGRESS BAR SECTION =====
        bar_x, bar_y = 180, 170
        bar_w, bar_h = 680, 32
        
        draw.rounded_rectangle([bar_x + 2, bar_y + 2, bar_x + bar_w + 2, bar_y + bar_h + 2], 
                               radius=16, fill=(0, 0, 0, 50))
        
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], 
                               radius=16, fill=PROGRESS_BG, outline=ACCENT_DARK, width=1)
        
        fill_width = int((bar_w - 4) * min(progress / 100.0, 1.0))
        if fill_width > 0:
            draw.rounded_rectangle([bar_x + 2, bar_y + 2, bar_x + 2 + fill_width, bar_y + bar_h - 2], 
                                   radius=14, fill=ACCENT)
            if show_shine:
                draw.rounded_rectangle([bar_x + 2, bar_y + 2, bar_x + 2 + fill_width, bar_y + (bar_h - 2) // 2], 
                                       radius=14, fill=ACCENT_LIGHT)
        
        progress_text = f"{min(progress, 100):.0f}%"
        pct_bbox = draw.textbbox((0, 0), progress_text, font=font_md)
        pct_w = pct_bbox[2] - pct_bbox[0]
        pct_h = pct_bbox[3] - pct_bbox[1]
        
        text_x = bar_x + bar_w // 2 - pct_w // 2
        text_y = bar_y - 3 + bar_h // 2 - pct_h // 2
        
        draw.text((text_x + 1, text_y + 1), progress_text, fill=(0, 0, 0, 100), font=font_md)
        draw.text((text_x, text_y), progress_text, fill=TEXT_PRIMARY, font=font_md)
        
        xp_text = f"{xp:,} / {xp_needed:,} XP"
        draw.text((bar_x, bar_y + bar_h + 12), xp_text, fill=TEXT_SECONDARY, font=font_sm)
        
        scale = 0.45
        new_size = (int(WIDTH * scale), int(HEIGHT * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return discord.File(buffer, filename="level_card.png")

    @staticmethod
    def create_container(
        title: str,
        description: str,
        *,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        accent_color: discord.Color = None,
        accessories: List[discord.ui.ActionRow | discord.ui.Thumbnail] = None
    ) -> discord.ui.Container:
        section_children = [f"## {title}\n{description}"]
        if image:
            section_children.append(discord.ui.MediaGallery(discord.MediaGalleryItem(url=image)))
            
        section = discord.ui.Section(
            *section_children,
            accessory=accessories[0] if accessories else (discord.ui.Thumbnail(thumbnail) if thumbnail else None)
        )
        
        container = discord.ui.Container(
            section,
            accent_color=accent_color or EmbedComponent.DEFAULT_COLOR
        )
        
        if accessories and len(accessories) > 1:
            for acc in accessories[1:]:
                container.add_item(acc)
                
        return container
