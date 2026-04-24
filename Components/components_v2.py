import discord
from discord import ui
from typing import Optional, Callable, Any, List


class BaseLayoutView(ui.LayoutView):
    
    def __init__(self, user: Optional[discord.User | discord.Member] = None, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.user and interaction.user.id != self.user.id:
            await interaction.response.send_message("This component is not for you!", ephemeral=True)
            return False
        return True
    
    def add_container(self, container: ui.Container):
        self.add_item(container)


class ButtonLayoutView(BaseLayoutView):
    
    def __init__(
        self,
        user: Optional[discord.User | discord.Member] = None,
        timeout: float = 180.0,
        on_timeout: Callable = None,
        **kwargs
    ):
        super().__init__(user=user, timeout=timeout)
        self._on_timeout = on_timeout
    
    async def on_timeout(self):
        if self._on_timeout:
            self._on_timeout()


class ConfirmView(ButtonLayoutView):
    
    def __init__(
        self,
        user: Optional[discord.User | discord.Member] = None,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        confirm_style: discord.ButtonStyle = discord.ButtonStyle.success,
        cancel_style: discord.ButtonStyle = discord.ButtonStyle.danger,
        timeout: float = 60.0,
        **kwargs
    ):
        super().__init__(timeout=timeout, user=user)
        self.confirmed = False
        
        self.btn_confirm = ui.Button(
            label=confirm_label,
            style=confirm_style,
            custom_id="confirm"
        )
        self.btn_confirm.callback = self._confirm_callback
        
        self.btn_cancel = ui.Button(
            label=cancel_label,
            style=cancel_style,
            custom_id="cancel"
        )
        self.btn_cancel.callback = self._cancel_callback
        
        self.container = ui.Container(
            ui.Section(
                "Do you want to proceed?",
                accessory=ui.ActionRow(self.btn_confirm, self.btn_cancel),
            ),
            accent_color=discord.Color.blurple()
        )
        self.add_item(self.container)
    
    async def _confirm_callback(self, interaction: discord.Interaction):
        self.confirmed = True
        await interaction.response.send_message("Confirmed!", ephemeral=True)
        self.stop()
    
    async def _cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Cancelled.", ephemeral=True)
        self.stop()


def create_info_view(
    title: str,
    content: str,
    buttons: List[dict] = None,
    *,
    user: Optional[discord.User | discord.Member] = None,
    color: discord.Color = None,
    thumbnail_url: str = None,
) -> ButtonLayoutView:
    
    view = ButtonLayoutView(user=user)
    
    button_items = []
    if buttons:
        for btn in buttons:
            b = ui.Button(
                label=btn.get("label", "Button"),
                style=btn.get("style", discord.ButtonStyle.secondary),
                emoji=btn.get("emoji"),
                custom_id=btn.get("id", btn.get("label", "button").lower().replace(" ", "_"))
            )
            
            async def callback(interaction, button=b):
                await interaction.response.send_message(f"Clicked: {button.custom_id}", ephemeral=True)
            
            b.callback = callback
            button_items.append(b)
    
    section_children = [title + "\n" + content]
    if thumbnail_url:
        section_children.append(ui.Thumbnail(thumbnail_url))
    
    if button_items:
        section_children.append(ui.ActionRow(*button_items))
    
    container = ui.Container(
        ui.Section(*section_children),
        accent_color=color or discord.Color.blurple()
    )
    view.add_item(container)
    
    return view


LayoutViewBase = BaseLayoutView


__all__ = [
    "BaseLayoutView",
    "LayoutViewBase",
    "ButtonLayoutView",
    "ConfirmView",
    "create_info_view",
]