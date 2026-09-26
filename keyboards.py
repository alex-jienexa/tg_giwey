from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_channels_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопки с сохраненными каналами
    for ch in channels:
        builder.button(
            text=f"📢 {ch['title']}", 
            callback_data=f"select_channel:{ch['channel_id']}"
        )
    
    # Кнопка добавления нового канала
    builder.button(
        text="➕ Добавить новый канал", 
        callback_data="add_new_channel"
    )
    
    # Выравниваем сохраненные каналы по 1 в ряд
    builder.adjust(1)
    return builder.as_markup()

def get_manage_channels_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    """Список сохраненных каналов с кнопками управления"""
    builder = InlineKeyboardBuilder()
    
    for ch in channels:
        builder.button(
            text=f"📢 {ch['title']}", 
            callback_data=f"manage_ch:{ch['channel_id']}"
        )
    
    builder.button(text="➕ Добавить канал", callback_data="add_new_channel_manage")
    builder.adjust(1)
    return builder.as_markup()

def get_channel_detail_keyboard(channel_id: str) -> InlineKeyboardMarkup:
    """Карточка канала: удалить или вернуться назад"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="❌ Удалить из списка", callback_data=f"delete_ch:{channel_id}")
    builder.button(text="🔙 Назад к списку", callback_data="back_to_channels")
    builder.adjust(1)
    return builder.as_markup()