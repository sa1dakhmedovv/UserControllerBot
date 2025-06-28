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


SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ---------- BOT INIT ----------
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

YOUR_ADMIN_ID = 5802051984
controller = UserbotController(API_ID, API_HASH, bot=bot, admin_id=YOUR_ADMIN_ID)

# ---------- STATES for /newsession ----------
class NewSessionStates(StatesGroup):
    waiting_for_session_name = State()
    waiting_for_phone = State()
    waiting_for_code = State()

# ---------- START ----------
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 Avto Guruh Yaratish BOT\n\n"
        "✅ /newsession – yangi Telegram session yaratish\n"
        "✅ /add session_name Guruh_Nomi Username [start_index]\n"
        "✅ /status"
        "✅ /stop session_name\n"
        "✅ /stopall\n"
        "✅ /setdelay sekundlar – guruhlar orasidagi kutish vaqtini sozlash"
    )

# ---------- /newsession QISM ----------
@dp.message_handler(commands=['newsession'])
async def cmd_newsession(message: types.Message):
    await message.answer("🗂️ Session fayli uchun nom kiriting (masalan: acc1):")
    await NewSessionStates.waiting_for_session_name.set()


@dp.message_handler(state=NewSessionStates.waiting_for_session_name)
async def process_session_name(message: types.Message, state: FSMContext):
    session_name = message.text.strip()
    await state.update_data(session_name=session_name)
    await message.answer("📱 Telefon raqamingizni yuboring (+998...):")
    await NewSessionStates.waiting_for_phone.set()


@dp.message_handler(state=NewSessionStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)

    data = await state.get_data()
    session_name = data['session_name']
    session_path = os.path.join(SESSIONS_DIR, session_name)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    try:
        result = await client.send_code_request(phone)
        await client.disconnect()

        await state.update_data(phone_code_hash=result.phone_code_hash)
        await state.update_data(client_phone=phone)

        await message.answer("📨 SMS kodi yuborildi. Kodni kiriting:")
        await NewSessionStates.waiting_for_code.set()

    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ Kod yuborishda xatolik: {e}")
        await state.finish()



@dp.message_handler(state=NewSessionStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()

    session_name = data['session_name']
    phone = data['client_phone']
    phone_code_hash = data['phone_code_hash']
    session_path = os.path.join(SESSIONS_DIR, session_name)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        await client.disconnect()

        await message.answer(
            f"✅ Session yaratildi!\n👤 @{me.username}\n💾 Fayl: {session_path}.session"
        )
        await state.finish()

    except Exception as e:
        await client.disconnect()
        await message.answer(f"❌ Login xato: {e}")
        await state.finish()


# ---------- /add QISM (sening eski koding) ----------
@dp.message_handler(commands=['add'])
async def cmd_add(message: types.Message):
    args = message.get_args().split()
    if len(args) < 3:
        return await message.reply(
            "❗ To‘liq yozing:\n/add session_name Guruh_Nomi Username [start_index]"
        )

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

# ---------- /stop ----------
@dp.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    args = message.get_args().split()
    if not args:
        return await message.reply("❗ /stop <session_name>")
    session_name = args[0]
    res = await controller.stop_session(session_name)
    await message.reply(res)

# ---------- /stopall ----------
@dp.message_handler(commands=['stopall'])
async def cmd_stopall(message: types.Message):
    await controller.stop_all()
    await message.reply("✅ Barcha sessionlar to‘xtatildi.")

# ---------- /status ----------
@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    res = controller.get_status_all()
    await message.reply(res)

# ---------- BOT COMMANDS ----------
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni boshlash"),
        BotCommand(command="newsession", description="Yangi Telegram session yaratish"),
        BotCommand(command="add", description="Userbot sessionini ishga tushirish"),
        BotCommand(command="stop", description="Sessionni to'xtatish"),
        BotCommand(command="stopall", description="Barcha sessionlarni to'xtatish"),
        BotCommand(command="status", description="Sessionlar holatini ko'rish"),
        BotCommand(command="setdelay", description="Kutish vaqtini sozlash")
    ]
    await bot.set_my_commands(commands)

@dp.message_handler(commands=['setdelay'])
async def cmd_setdelay(message: types.Message):
    args = message.get_args().split()
    if not args:
        return await message.reply("❗ /setdelay <sekundlar>")

    try:
        seconds = int(args[0])
        controller.set_delay(seconds)
        await message.reply(f"✅ Guruhlar orasidagi kutish {seconds} soniyaga o'rnatildi.")
    except ValueError:
        await message.reply("❗ Son bo'lishi kerak!")


# ---------- MAIN ----------
if __name__ == '__main__':
    async def on_startup(dp):
        await set_commands(bot)
        print("✅ Komandalar o'rnatildi")

    executor.start_polling(dp, on_startup=on_startup)
