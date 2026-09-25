import secrets
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import create_giveaway, get_giveaway, get_participants, close_giveaway
from states import CreateGiveawayForm

admin_router = Router()

# Helper: построение меню управления для владельца
def get_management_keyboard(giveaway_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список участников", callback_data=f"manage_users_{giveaway_id}")],
        [InlineKeyboardButton(text="ℹ️ Информация о розыгрыше", callback_data=f"manage_info_{giveaway_id}")],
        [InlineKeyboardButton(text="🛑 Завершить досрочно", callback_data=f"manage_finish_{giveaway_id}")]
    ])

@admin_router.message(Command("create_giveaway_test"))
async def start_creation(message: Message, state: FSMContext):
    await state.set_state(CreateGiveawayForm.select_channel)
    await message.answer(
        "🛠 **Мастер создания розыгрыша**\n\n"
        "Шаг 1: Отправьте **@username** или **ID** вашего канала (например, `@my_test_channel` или `-100123456789`).\n"
        "⚠️ *Убедитесь, что бот предварительно добавлен в этот канал администратором!*",
        parse_mode="Markdown"
    )

@admin_router.message(CreateGiveawayForm.select_channel)
async def process_channel(message: Message, state: FSMContext, bot: Bot):
    channel_id = message.text.strip()
    
    # Проверяем, является ли бот админом в этом канале
    try:
        chat = await bot.get_chat(channel_id)
        bot_member = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.answer("❌ Бот находится в канале, но не имеет прав администратора. Выдайте права админа и попробуйте снова.", parse_mode="Markdown")
            return
    except TelegramBadRequest:
        await message.answer("❌ Не удалось найти канал или бот в него не добавлен. Проверьте адрес и повторите ввод:", parse_mode="Markdown")
        return

    await state.update_data(channel_id=str(chat.id), channel_title=chat.title)
    await state.set_state(CreateGiveawayForm.enter_title)
    await message.answer(f"✅ Канал **{chat.title}** подтвержден!\n\nШаг 2: Введите **название розыгрыша**:", parse_mode="Markdown")

@admin_router.message(CreateGiveawayForm.enter_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateGiveawayForm.enter_winners_count)
    await message.answer("Шаг 3: Введите **количество призовых мест (победителей)** (целое число):", parse_mode="Markdown")

@admin_router.message(CreateGiveawayForm.enter_winners_count)
async def process_winners(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Пожалуйста, введите корректное положительное число.", parse_mode="Markdown")
        return
    
    await state.update_data(winners_count=int(message.text))
    await state.set_state(CreateGiveawayForm.enter_end_time)
    await message.answer("Шаг 4: Введите **срок проведения** (например: `24 часа`, `3 дня` или конкретную дату `30.09.2026`):", parse_mode="Markdown")

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