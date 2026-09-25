from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject
from aiogram.exceptions import TelegramBadRequest

from database import get_giveaway, add_participant

user_router = Router()

async def check_subscription(bot: Bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except TelegramBadRequest:
        return False

@user_router.message(CommandStart(deep_link=True))
async def handle_deep_link_start(message: Message, command: CommandObject, bot: Bot):
    args = command.args # Например: "join_a3f89e12b40c"
    
    if not args or not args.startswith("join_"):
        await message.answer("Добро пожаловать! Бот готов к работе.")
        return

    giveaway_id = args.split("_")[1]
    giveaway = await get_giveaway(giveaway_id)

    if not giveaway or not giveaway[6]: # is_active
        await message.answer("❌ Данный розыгрыш не существует или уже завершен.")
        return

    channel_id = giveaway[3]
    user_id = message.from_user.id

    # Проверка подписки на канал
    is_subscribed = await check_subscription(bot, channel_id, user_id)
    if not is_subscribed:
        await message.answer(
            f"❌ **Вы не подписаны на канал розыгрыша!**\n\n"
            f"Пожалуйста, подпишитесь на канал и нажмите на кнопку в посте ещё раз."
        )
        return

    # Запись в БД
    is_new = await add_participant(giveaway_id, user_id)
    if is_new:
        await message.answer(f"🎉 **Отлично!** Вы успешно зарегистрированы в розыгрыше «**{giveaway[2]}**»!")
    else:
        await message.answer(f"ℹ️ Вы уже принимаете участие в розыгрыше «**{giveaway[2]}**».")

@user_router.message(CommandStart())
async def handle_regular_start(message: Message):
    await message.answer("Привет! Воспользуйтесь командой `/create_giveaway_test`, чтобы составить новый розыгрыш.")