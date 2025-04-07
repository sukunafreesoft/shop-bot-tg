import json
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.utils.markdown import hcode
from aiogram.client.default import DefaultBotProperties
import asyncio

# Получаем токен из переменной окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден. Убедитесь, что он указан в Railway переменных окружения.")

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# Загрузка товаров
with open("products.json", "r", encoding="utf-8") as f:
    products = json.load(f)

# Загрузка пользователей
if os.path.exists("users.json"):
    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)
else:
    users = {}

# /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    user_id = str(user.id)
    ref_code = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
        "referral_code": ref_code if ref_code != user_id else None,
        "joined_at": now,
        "invited_by": ref_code if ref_code != user_id else None
    }

    if user_id not in users:
        users[user_id] = user_data
        if ref_code and ref_code != user_id and ref_code in users:
            users[ref_code]["invited_count"] = users[ref_code].get("invited_count", 0) + 1
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)

    text = f"Привет, {user.first_name or 'друг'}!\n\n"
    if ref_code:
        text += f"Ты зашёл по реферальной ссылке: {ref_code}\n\n"

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="📦 Каталог")],
        [KeyboardButton(text="👤 Профиль")]
    ])
    await message.answer(text + "Используй кнопки ниже для взаимодействия с ботом.", reply_markup=keyboard)

# Каталог
@router.message(F.text == "📦 Каталог")
async def show_catalog(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=product["name"], callback_data=f"product_{product['id']}")]
        for product in products
    ])
    await message.answer("Выберите товар:", reply_markup=keyboard)

# Товар
@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = next((p for p in products if p['id'] == product_id), None)

    if not product:
        await callback.message.answer("Товар не найден.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Купить", url=product['url'])]
    ])
    if product.get("image"):
        await callback.message.answer_photo(
            product["image"],
            caption=product["description"],
            reply_markup=keyboard
        )
    else:
        await callback.message.answer(product["description"], reply_markup=keyboard)

# Профиль
@router.message(F.text == "👤 Профиль")
async def profile(message: Message):
    user = message.from_user
    user_id = str(user.id)
    user_data = users.get(user_id, {})
    invited_by = user_data.get("invited_by")
    joined_at = user_data.get("joined_at", "—")
    invited_count = user_data.get("invited_count", 0)

    invited_by_username = "—"
    if invited_by and invited_by in users:
        invited_user = await bot.get_chat(int(invited_by))
        invited_by_username = f"@{invited_user.username}" if invited_user.username else hcode(invited_by)

    text = (
        "<b>Информация о тебе:</b>\n\n"
        f"• <b>ID:</b> <code>{user.id}</code>\n"
        f"• <b>Имя:</b> {user.first_name or '—'}\n"
        f"• <b>Фамилия:</b> {user.last_name or '—'}\n"
        f"• <b>Юзернейм:</b> @{user.username or '—'}\n"
        f"• <b>Язык Telegram:</b> {user.language_code or '—'}\n"
        f"• <b>Когда пришёл:</b> {joined_at}\n"
        f"• <b>Кто пригласил:</b> {invited_by_username}\n"
        f"• <b>Сколько пригласил:</b> {invited_count}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        InlineKeyboardButton(text="Пригласить друга", callback_data=f"send_ref_link_{user.id}")
    ])
    await message.answer(text, reply_markup=keyboard)

# Реферальная ссылка
@router.callback_query(F.data.startswith("send_ref_link_"))
async def send_ref_link(call: CallbackQuery):
    user_id = call.data.split("_")[-1]
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    await call.message.answer(f"Твоя реферальная ссылка:\n{ref_link}")

# /get_ref_link
@router.message(Command("get_ref_link"))
async def get_ref_link(message: Message):
    user_id = message.from_user.id
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    await message.answer(f"Твоя реферальная ссылка:\n{ref_link}")

# Старт
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
