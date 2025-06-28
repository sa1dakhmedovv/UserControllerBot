import asyncio
import os
import time
from telethon import TelegramClient, errors
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.channels import CreateChannelRequest, InviteToChannelRequest


class UserbotController:
    def __init__(self, api_id, api_hash, bot=None, admin_id=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot = bot
        self.admin_id = admin_id

        self.delay_seconds = 5

        # sessionlar holati
        self.sessions = {}          # {session_name: {task, index, floodwait, floodwait_expire}}
        self.session_locks = {}     # 🔒 Lock har bir session uchun

    def set_delay(self, seconds):
        self.delay_seconds = seconds

    def get_status_all(self):
        if not self.sessions:
            return "🚫 Hech qanday session ishlamayapti."

        txt = "✅ Ishlayotgan sessionlar:\n"
        now = int(time.time())
        for name, data in self.sessions.items():
            indeks = data.get("index", "?")
            flood_expire = data.get("floodwait_expire", 0)

            remaining = max(0, flood_expire - now)
            txt += f"🟢 {name}: Ishlayapti. FloodWait={remaining}s, Next index={indeks}, delay={self.delay_seconds}\n"

        return txt

    async def report_error(self, where, error):
        msg = f"❌ Xatolik [{where}]:\n{error}"
        print(f"[ERROR] {where}: {error}")

        if self.bot and self.admin_id:
            try:
                await self.bot.send_message(self.admin_id, msg)
            except Exception as e:
                print(f"[BOTGA YUBORISHDA XATO]: {e}")

    async def create_group(self, client, title, user_to_add, session_name):
        async with self.session_locks[session_name]:
            try:
                # ✅ Guruh yaratish
                result = await client(CreateChannelRequest(
                    title=title,
                    about="Avto-created group",
                    megagroup=True
                ))
                chat = result.chats[0]

                # ✅ Foydalanuvchi qo'shish
                await client(InviteToChannelRequest(chat.id, [user_to_add]))

                # ✅ groups_sessions papkasini yarat
                os.makedirs("groups_sessions", exist_ok=True)

                # ✅ Log fayliga yozish
                with open(f"groups_sessions/{session_name}.txt", "a", encoding="utf-8") as f:
                    f.write(f"{title}\n")

            except (FloodWaitError, RPCError, errors.rpcerrorlist.YouBlockedUserError, errors.ChatAdminRequiredError) as e:
                await self.report_error("create_group RPCError", e)
                raise
            except Exception as e:
                await self.report_error("create_group Exception", e)
                raise

    async def auto_create_groups(self, session_name, client, group_title, user_to_add, start_index):
        indeks = start_index
        while True:
            try:
                await self.create_group(client, f"{group_title} {indeks}", user_to_add, session_name)
                indeks += 1

                if session_name in self.sessions:
                    self.sessions[session_name]["index"] = indeks
                    self.sessions[session_name]["floodwait_expire"] = 0

                await asyncio.sleep(self.delay_seconds)

            except FloodWaitError as e:
                wait_seconds = e.seconds
                now = int(time.time())
                if session_name in self.sessions:
                    self.sessions[session_name]["floodwait_expire"] = now + wait_seconds

                await self.report_error("auto_create_groups FloodWait", e)
                await asyncio.sleep(wait_seconds + 10)

            except RPCError as e:
                await self.report_error("auto_create_groups RPCError", e)
                break

            except Exception as e:
                await self.report_error("auto_create_groups Exception", e)
                break

    async def add_session(self, session_name, group_title, user_to_add, start_index=None):
        if session_name not in self.session_locks:
            self.session_locks[session_name] = asyncio.Lock()

        async with self.session_locks[session_name]:
            try:
                client = TelegramClient(f"sessions/{session_name}", self.api_id, self.api_hash)
                await client.start()

                if start_index is None:
                    try:
                        os.makedirs("groups_sessions", exist_ok=True)
                        with open(f"groups_sessions/{session_name}.txt", encoding="utf-8") as f:
                            lines = f.readlines()
                        start_index = len(lines) + 1
                    except FileNotFoundError:
                        start_index = 1

                task = asyncio.create_task(
                    self.auto_create_groups(session_name, client, group_title, user_to_add, start_index)
                )

                self.sessions[session_name] = {
                    "task": task,
                    "index": start_index,
                    "floodwait_expire": 0
                }

                return f"✅ Session '{session_name}' ishga tushdi. Start index: {start_index}"

            except Exception as e:
                await self.report_error("add_session", e)
                return f"❌ Session '{session_name}' ishga tushmadi: {e}"

    async def stop_session(self, session_name):
        if session_name in self.sessions:
            self.sessions[session_name]["task"].cancel()
            del self.sessions[session_name]
            return f"🛑 '{session_name}' to‘xtatildi."
        return f"🚫 Session '{session_name}' topilmadi."

    async def stop_all(self):
        for name in list(self.sessions.keys()):
            await self.stop_session(name)
