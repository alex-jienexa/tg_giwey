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