import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from telethon import TelegramClient
from controller import UserbotController

API_TOKEN = '7952096466:AAEtYQjEWlE7eYQ_vqnZifsC4F9Q7K7BnlY'
API_ID = 28369489
API_HASH = '369653d4ba4277f81d109368af59f82f'

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.utils import executor
from controller import UserbotController

# ✅ ADMIN TELEGRAM ID (agar xato yoki status yuborishni istasang)
ADMIN_ID = 5802051984

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ✅ UserbotController obyektini yaratamiz
controller = UserbotController(API_ID, API_HASH, bot=bot, admin_id=ADMIN_ID)

# /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    text = (
        "🤖 Avto Guruh Yaratish BOT\n\n"
        "✅ /add session_name Guruh_Nomi Username [start_index]\n"
        "✅ /stop session_name\n"
        "✅ /stopall\n"
        "✅ /status\n"
        "✅ /setdelay sekundlar"
    )
    await message.answer(text)

# /add
@dp.message_handler(commands=['add'])
async def cmd_add(message: types.Message):
    args = message.get_args().split()
    if len(args) < 3:
        return await message.reply("❗ To‘liq yozing:\n/add session_name Guruh_Nomi Username [start_index]")

    session_name = args[0]
    group_title = args[1]
    user_to_add = args[2]

    start_index = None
    if len(args) >= 4:
        try:
            start_index = int(args[3])
        except ValueError:
            return await message.reply("❗ start_index butun son bo‘lishi kerak!")

    res = await controller.add_session(session_name, group_title, user_to_add, start_index)
    await message.reply(res)

# /stop
@dp.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    args = message.get_args().split()
    if not args:
        return await message.reply("❗ /stop <session_name>")
    session_name = args[0]
    res = await controller.stop_session(session_name)
    await message.reply(res)

# /stopall
@dp.message_handler(commands=['stopall'])
async def cmd_stopall(message: types.Message):
    await controller.stop_all()
    await message.reply("✅ Barcha sessionlar to‘xtatildi.")

# /status
@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    res = controller.get_status_all()
    await message.reply(res)

# /setdelay
@dp.message_handler(commands=['setdelay'])
async def cmd_setdelay(message: types.Message):
    args = message.get_args().split()
    if not args:
        return await message.reply("❗ /setdelay <sekundlar>")
    try:
        seconds = int(args[0])
        controller.set_delay(seconds)
        await message.reply(f"✅ Delay {seconds} sekundga o'rnatildi.")
    except ValueError:
        await message.reply("❗ Delay butun son bo‘lishi kerak.")

# Bot buyruqlari
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni boshlash"),
        BotCommand(command="add", description="Yangi session qo'shish"),
        BotCommand(command="stop", description="Sessionni to'xtatish"),
        BotCommand(command="stopall", description="Barcha sessionlarni to'xtatish"),
        BotCommand(command="status", description="Barcha sessionlar holati"),
        BotCommand(command="setdelay", description="Delay vaqtini o'zgartirish"),
    ]
    await bot.set_my_commands(commands)

if __name__ == '__main__':
    async def on_startup(dp):
        await set_commands(bot)
        print("✅ Bot komandalar o'rnatildi va ishga tushdi")

    executor.start_polling(dp, on_startup=on_startup)
