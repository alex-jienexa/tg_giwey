import secrets
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import create_giveaway, get_giveaway, get_participants, close_giveaway, get_user_channels, save_channel, delete_channel
from keyboards import get_channels_keyboard, get_channel_detail_keyboard, get_manage_channels_keyboard, get_cancel_inline_keyboard
from states import CreateGiveawayForm, ChannelManageFS

admin_router = Router()

# Helper: построение меню управления для владельца
def get_management_keyboard(giveaway_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список участников", callback_data=f"manage_users_{giveaway_id}")],
        [InlineKeyboardButton(text="ℹ️ Информация о розыгрыше", callback_data=f"manage_info_{giveaway_id}")],
        [InlineKeyboardButton(text="🛑 Завершить досрочно", callback_data=f"manage_finish_{giveaway_id}")]
    ])

# Отмена всех FSM-состояний
@admin_router.message(F.text.in_({"❌ Отмена", "/cancel"}))
async def process_cancel_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять.", reply_markup=ReplyKeyboardRemove())
        return

    await state.clear()
    await message.answer(
        "🚫 Действие отменено.", 
        reply_markup=ReplyKeyboardRemove()
    )

@admin_router.callback_query(F.data == "cancel_fsm")
async def process_cancel_callback(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await callback.answer("Действие уже отменено или неактивно.")
        return

    await state.clear()
    await callback.message.edit_text("🚫 Действие отменено.")
    await callback.answer()


@admin_router.message(Command("create_giveaway_test"))
async def start_creation(message: Message, state: FSMContext):
    user_channels = await get_user_channels(message.from_user.id)

    if user_channels:
        await message.answer(
            "🛠 **Мастер создания розыгрыша**\n\n"
            "Выберите канал из списка сохраненных или добавьте новый:",
            parse_mode="Markdown",
            reply_markup=get_channels_keyboard(user_channels)
        )
        await state.set_state(CreateGiveawayForm.select_channel)
    else:
        await message.answer(
            "🛠 **Мастер создания розыгрыша**\n\n"
            "Шаг 1: Отправьте **@username** или **ID** вашего канала (например, `@my_test_channel` или `-100123456789`).\n"
            "⚠️ *Убедитесь, что бот предварительно добавлен в этот канал администратором!*",
            parse_mode="Markdown",
            reply_markup=get_cancel_inline_keyboard()
        )
        await state.set_state(CreateGiveawayForm.input_channel_manually)

@admin_router.message(Command("channels"))
async def cmd_manage_channels(message: Message):
    user_channels = await get_user_channels(message.from_user.id)
    
    if not user_channels:
        await message.answer(
            "📋 **Ваш список каналов пуст.**\n\n"
            "Вы можете добавить канал, чтобы быстро выбирать его при создании розыгрышей.",
            parse_mode="Markdown",
            reply_markup=get_manage_channels_keyboard([])
        )
        return

    await message.answer(
        "📋 **Управление сохраненными каналами**\n\n"
        "Выберите канал для настройки или удалите устаревший:",
        parse_mode="Markdown",
        reply_markup=get_manage_channels_keyboard(user_channels)
    )


@admin_router.callback_query(CreateGiveawayForm.select_channel, F.data.startswith("select_channel:"))
async def on_channel_selected(callback: CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = callback.data.split(":")[1]
    
    # Проверяем, доступен ли канал до сих пор
    try:
        chat = await bot.get_chat(channel_id)
        await state.update_data(channel_id=chat.id, channel_title=chat.title)
        
        await callback.message.edit_text(
            f"✅ Канал **{chat.title}** выбран!\n\n"
            f"Шаг 2: Введите **название розыгрыша**:",
            parse_mode="Markdown",
            reply_markup=get_cancel_inline_keyboard()
        )
        await state.set_state(CreateGiveawayForm.enter_title)
    except TelegramBadRequest:
        await callback.answer("❌ Бот был удален из этого канала или нет прав!", show_alert=True)

@admin_router.message(CreateGiveawayForm.input_channel_manually)
async def process_channel(message: Message, state: FSMContext, bot: Bot):
    channel_id = message.text.strip()
    
    # Проверяем, является ли бот админом в этом канале
    try:
        chat = await bot.get_chat(channel_id)
        bot_member = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.answer("❌ Бот находится в канале, но не имеет прав администратора. Выдайте права админа и попробуйте снова.", parse_mode="Markdown", reply_markup=get_cancel_inline_keyboard())
            return
        # Сохраняем канал в базу данных для этого пользователя
        await save_channel(
            user_id=message.from_user.id,
            channel_id=str(chat.id if chat.username is None else f"@{chat.username}"),
            title=chat.title
        )
    except TelegramBadRequest:
        await message.answer("❌ Не удалось найти канал или бот в него не добавлен. Проверьте адрес и повторите ввод:", parse_mode="Markdown", reply_markup=get_cancel_inline_keyboard())
        return

    await state.update_data(channel_id=str(chat.id), channel_title=chat.title)
    await state.set_state(CreateGiveawayForm.enter_title)
    await message.answer(f"✅ Канал **{chat.title}** подтвержден!\n\nШаг 2: Введите **название розыгрыша**:", parse_mode="Markdown", reply_markup=get_cancel_inline_keyboard())

@admin_router.message(CreateGiveawayForm.enter_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateGiveawayForm.enter_winners_count)
    await message.answer("Шаг 3: Введите **количество призовых мест (победителей)** (целое число):", parse_mode="Markdown", reply_markup=get_cancel_inline_keyboard())

@admin_router.message(CreateGiveawayForm.enter_winners_count)
async def process_winners(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Пожалуйста, введите корректное положительное число.", parse_mode="Markdown", reply_markup=get_cancel_inline_keyboard())
        return
    
    await state.update_data(winners_count=int(message.text))
    await state.set_state(CreateGiveawayForm.enter_end_time)
    await message.answer("Шаг 4: Введите **срок проведения** (например: `24 часа`, `3 дня` или конкретную дату `30.09.2026`):", parse_mode="Markdown", reply_markup=get_cancel_inline_keyboard())

@admin_router.message(CreateGiveawayForm.enter_end_time)
async def process_end_time(message: Message, state: FSMContext, bot: Bot):
    end_time_str = message.text.strip()
    data = await state.get_data()
    await state.clear()

    # Сохраняем в базу
    giveaway_id = await create_giveaway(
        creator_id=message.from_user.id,
        title=data['title'],
        channel_id=data['channel_id'],
        winners_count=data['winners_count'],
        end_time=end_time_str
    )

    # 1. Публикуем анонс в самом канале
    # Кнопка ведет в ЛС бота с deep-link параметром
    bot_info = await bot.get_me()
    join_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Участвовать 🎁", url=f"https://t.me/{bot_info.username}?start=join_{giveaway_id}")]
    ])

    post_text = (
        f"🎁 **РОЗЫГРЫШ: {data['title']}**\n\n"
        f"📌 **Условие:** Подписка на этот канал\n"
        f"🏆 **Победителей:** {data['winners_count']}\n"
        f"⏳ **Срок:** {end_time_str}\n\n"
        f"Жмите кнопку ниже для участия!"
    )

    try:
        await bot.send_message(chat_id=data['channel_id'], text=post_text, reply_markup=join_button, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при публикации поста в канал: {e}")

    # 2. Отправляем меню управления управляющему
    await message.answer(
        f"🎉 **Розыгрыш успешно создан и опубликован!**\n\n"
        f"Управление розыгрышем — **{data['title']}** (ID: `{giveaway_id}`)",
        reply_markup=get_management_keyboard(giveaway_id),
        parse_mode="Markdown"
    )

# --- Панель Управления Розыгрышем ---

@admin_router.callback_query(F.data.startswith("manage_users_"))
async def callback_list_users(callback: CallbackQuery):
    giveaway_id = callback.data.split("_")[2]
    giveaway = await get_giveaway(giveaway_id)

    if not giveaway or callback.from_user.id != giveaway[1]: # creator_id
        await callback.answer("У вас нет прав для управления этим розыгрышем.", show_alert=True)
        return

    participants = await get_participants(giveaway_id)
    if not participants:
        await callback.answer("Участников пока нет.", show_alert=True)
        return

    users_text = "\n".join([f"{idx + 1}. [{uid}](tg://user?id={uid})" for idx, uid in enumerate(participants)])
    await callback.message.answer(
        f"📋 **Список участников розыгрыша `{giveaway_id}`** (Всего: {len(participants)}):\n\n{users_text}",
        parse_mode="Markdown"
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("manage_info_"))
async def callback_info(callback: CallbackQuery):
    giveaway_id = callback.data.split("_")[2]
    giveaway = await get_giveaway(giveaway_id)

    if not giveaway or callback.from_user.id != giveaway[1]:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    status = "Активен 🟢" if giveaway[6] else "Завершен 🔴"
    participants = await get_participants(giveaway_id)

    await callback.message.answer(
        f"ℹ️ **Информация о розыгрыше `{giveaway_id}`**\n\n"
        f"**Название:** {giveaway[2]}\n"
        f"**Статус:** {status}\n"
        f"**Победителей запланировано:** {giveaway[4]}\n"
        f"**Срок:** {giveaway[5]}\n"
        f"**Всего участников:** {len(participants)}",
        parse_mode="Markdown"
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("manage_finish_"))
async def callback_finish(callback: CallbackQuery, bot: Bot):
    giveaway_id = callback.data.split("_")[2]
    giveaway = await get_giveaway(giveaway_id)

    if not giveaway or callback.from_user.id != giveaway[1]:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    if not giveaway[6]: # is_active
        await callback.answer("Этот розыгрыш уже завершен!", show_alert=True)
        return

    participants = await get_participants(giveaway_id)
    if not participants:
        await callback.message.answer("❌ Розыгрыш нельзя подвести: нет ни одного участника.")
        await callback.answer()
        return

    # Выбор случайных победителей
    winners_count = min(giveaway[4], len(participants))
    winner_ids_list = secrets.SystemRandom().sample(participants, winners_count)
    winners_str = ",".join(map(str, winner_ids_list))

    await close_giveaway(giveaway_id, winners_str)

    # 1. Уведомление в чат управляющего
    winners_mentions = "\n".join([f"• [{uid}](tg://user?id={uid})" for uid in winner_ids_list])
    await callback.message.answer(
        f"🏁 **Розыгрыш `{giveaway_id}` подведен досрочно!**\n\n"
        f"🎉 **Победители:**\n{winners_mentions}",
        parse_mode="Markdown"
    )

    # 2. Уведомление в канал
    try:
        await bot.send_message(
            chat_id=giveaway[3],
            text=f"🏁 **Розыгрыш «{giveaway[2]}» завершен!**\n\n🎉 Победители:\n{winners_mentions}",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Не удалось отправить итоги в канал: {e}")

    # 3. Личное сообщение всем победителям
    for w_id in winner_ids_list:
        try:
            await bot.send_message(chat_id=w_id, text=f"🥳 **Поздравляем!** Вы выиграли в розыгрыше «{giveaway[2]}»!", parse_mode="Markdown")
        except TelegramForbiddenError:
            pass

    await callback.answer("Итоги успешно подведены!", show_alert=True)

# --- Управление каналами ---

@admin_router.callback_query(F.data == "back_to_channels")
async def back_to_channels_handler(callback: CallbackQuery):
    user_channels = await get_user_channels(callback.from_user.id)
    await callback.message.edit_text(
        "📋 <b>Управление сохраненными каналами</b>\n\n"
        "Выберите канал для настройки или удалите устаревший:",
        parse_mode="HTML",
        reply_markup=get_manage_channels_keyboard(user_channels)
    )

# --- КАРТОЧКА КАНАЛА ---

@admin_router.callback_query(F.data.startswith("manage_ch:"))
async def on_channel_detail_click(callback: CallbackQuery, bot: Bot):
    channel_id = callback.data.split(":")[1]
    
    # Проверяем актуальный статус бота в канале
    try:
        chat = await bot.get_chat(channel_id)
        member = await bot.get_chat_member(chat.id, bot.id)
        status_str = "✅ Бот является администратором" if member.status in ("administrator", "creator") else "⚠️ У бота нет прав администратора!"
        
        # Обновляем название канала в БД на случай, если его переименовали
        await save_channel(callback.from_user.id, channel_id, chat.title)
        title = chat.title
    except Exception:
        status_str = "❌ Канал недоступен или бот был удален из него"
        title = channel_id

    await callback.message.edit_text(
        f"📢 **Канал:** {title}\n"
        f"**ID/Username:** `{channel_id}`\n"
        f"**Статус:** {status_str}",
        parse_mode="Markdown",
        reply_markup=get_channel_detail_keyboard(channel_id)
    )

# --- УДАЛЕНИЕ КАНАЛА ИЗ БАЗЫ ---

@admin_router.callback_query(F.data.startswith("delete_ch:"))
async def on_delete_channel_click(callback: CallbackQuery):
    channel_id = callback.data.split(":")[1]
    
    await delete_channel(callback.from_user.id, channel_id)
    await callback.answer("🗑 Канал удален из вашего списка!", show_alert=True)
    
    # Возвращаем пользователя к обновленному списку
    user_channels = await get_user_channels(callback.from_user.id)
    await callback.message.edit_text(
        "📋 **Управление сохраненными каналами**\n\n"
        "Канал успешно удален. Выберите канал из списка:",
        parse_mode="Markdown",
        reply_markup=get_manage_channels_keyboard(user_channels)
    )

# --- ДОБАВЛЕНИЕ КАНАЛА ЧЕРЕЗ МЕНЮ УПРАВЛЕНИЯ ---

@admin_router.callback_query(F.data == "add_new_channel_manage")
async def on_add_channel_manage_click(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "➕ **Добавление канала**\n\n"
        "Отправьте @username или ID канала (например, `@my_test_channel` или `-100123456789`).\n"
        "⚠️ *Предварительно добавьте бота в канал как администратора!*",
        parse_mode="Markdown"
    )
    await state.set_state(ChannelManageFS.waiting_for_channel)

@admin_router.message(ChannelManageFS.waiting_for_channel)
async def process_add_channel_manage(message: Message, state: FSMContext, bot: Bot):
    channel_input = message.text.strip()
    
    try:
        chat = await bot.get_chat(channel_input)
        member = await bot.get_chat_member(chat.id, bot.id)
        
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Бот не является администратором в этом канале! Добавьте его и попробуйте снова.")
            return

        ch_id = chat.id if chat.username is None else f"@{chat.username}"
        await save_channel(message.from_user.id, str(ch_id), chat.title)
        await state.clear()
        
        user_channels = await get_user_channels(message.from_user.id)
        await message.answer(
            f"✅ Канал **{chat.title}** успешно сохранен!\n\n"
            f"📋 **Управление сохраненными каналами:**",
            parse_mode="Markdown",
            reply_markup=get_manage_channels_keyboard(user_channels)
        )
    except Exception:
        await message.answer("❌ Не удалось найти канал. Проверьте правильность написания и наличие бота в канале.")