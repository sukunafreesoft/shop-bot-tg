import json
import logging
import os
from datetime import datetime
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram import Client
from aiogram import types

API_TOKEN = '7118250572:AAFXeQZSewrBqvlsnmiCViWGjhiI8HlLmI0'  # Замени на свой

logging.basicConfig(level=logging.INFO)

# Создание объекта Bot и Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Загрузка товаров
with open('products.json', 'r') as f:
    products = json.load(f)

# Загрузка пользователей
if os.path.exists("users.json"):
    with open("users.json", "r") as f:
        users = json.load(f)
else:
    users = {}

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    ref_code = message.get_args()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Получение информации о пользователе
    user = message.from_user
    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
        "referral_code": ref_code if ref_code != user_id else None,
        "joined_at": now,
        "invited_by": ref_code if ref_code != user_id else None,
        "device_info": message.from_user.device if hasattr(message.from_user, 'device') else 'Unknown',  # Информация об устройстве (если доступна)
    }

    if user_id not in users:
        users[user_id] = user_data
        if ref_code and ref_code != user_id:
            if ref_code in users:
                users[ref_code]["invited_count"] += 1
        with open("users.json", "w") as f:
            json.dump(users, f, indent=2)

    text = f"Привет, {message.from_user.first_name}!"
    if ref_code:
        text += f"\nТы зашёл по реферальной ссылке: {ref_code}"

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("📦 Каталог"))
    keyboard.add(types.KeyboardButton("👤 Профиль"))
    text += "\n\nИспользуй кнопки ниже для взаимодействия с ботом."
    await message.answer(text, reply_markup=keyboard)

# Обработка кнопки "Каталог"
@dp.message_handler(lambda message: message.text == "📦 Каталог")
async def show_catalog(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for product in products:
        button = types.InlineKeyboardButton(
            text=product['name'],
            callback_data=f"product_{product['id']}"
        )
        keyboard.add(button)
    await message.answer("Выберите товар:", reply_markup=keyboard)

# Обработка товаров
@dp.callback_query_handler(lambda c: c.data.startswith("product_"))
async def show_product(call: types.CallbackQuery):
    product_id = int(call.data.split("_")[1])
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        await call.message.answer("Товар не найден.")
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Купить", url=product['url']))
    if product.get("image"):
        await call.message.answer_photo(
            product["image"],
            caption=product["description"],
            reply_markup=keyboard
        )
    else:
        await call.message.answer(
            product["description"],
            reply_markup=keyboard
        )

# Обработка кнопки "Профиль"
@dp.message_handler(lambda message: message.text == "👤 Профиль")
async def profile(message: types.Message):
    user = message.from_user
    user_id = str(user.id)

    user_data = users.get(user_id, {})
    invited_by = user_data.get("invited_by")
    joined_at = user_data.get("joined_at", "—")
    invited_count = user_data.get("invited_count", 0)

    # Получаем юзернейм пригласившего пользователя
    invited_by_username = None
    if invited_by and invited_by in users:
        invited_by_user = await bot.get_chat(invited_by)
        invited_by_username = invited_by_user.username

    # Если у пригласившего нет юзернейма, показываем ID
    invited_by_display = invited_by_username if invited_by_username else (invited_by or '—')

    text = (
        "<b>Информация о тебе:</b>\n\n"
        f"• <b>ID:</b> <code>{user.id}</code>\n"
        f"• <b>Имя:</b> {user.first_name or '—'}\n"
        f"• <b>Фамилия:</b> {user.last_name or '—'}\n"
        f"• <b>Юзернейм:</b> @{user.username or '—'}\n"
        f"• <b>Язык Telegram:</b> {user.language_code or '—'}\n"
        f"• <b>Когда пришёл:</b> {joined_at}\n"
        f"• <b>Кто пригласил:</b> <code>{invited_by_display}</code>\n"
        f"• <b>Сколько пригласил:</b> {invited_count}"
    )

    keyboard = types.InlineKeyboardMarkup()
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user.id}"
    invite_button = types.InlineKeyboardButton("Пригласить друга", callback_data=f"send_ref_link_{user.id}")
    keyboard.add(invite_button)

    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

# Обработка команды, которая будет отправлять реферальную ссылку
@dp.callback_query_handler(lambda c: c.data.startswith("send_ref_link_"))
async def send_ref_link(call: types.CallbackQuery):
    user_id = call.data.split("_")[-1]
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    await call.message.answer(f"Твоя реферальная ссылка:\n{ref_link}")

# Команда /get_ref_link
@dp.message_handler(commands=['get_ref_link'])
async def get_ref_link(message: types.Message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    await message.answer(f"Твоя реферальная ссылка:\n{ref_link}")

# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
