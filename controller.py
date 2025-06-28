import asyncio
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
        self.sessions = {}
        self.session_locks = {}   # 🔒 Har bir session uchun Lock

    def set_delay(self, seconds):
        self.delay_seconds = seconds

    def get_status_all(self):
        if not self.sessions:
            return "🚫 Hech qanday session ishlamayapti."

        txt = "✅ Ishlayotgan sessionlar:\n"
        for name, data in self.sessions.items():
            indeks = data.get("index", "?")
            flood = data.get("floodwait", 0)
            txt += f"🟢 {name}: Ishlayapti. FloodWait={flood}s, Next index={indeks}, delay={self.delay_seconds}\n"
        return txt

    async def report_error(self, where, error):
        if self.bot and self.admin_id:
            try:
                msg = f"❌ Xatolik [{where}]:\n{error}"
                await self.bot.send_message(self.admin_id, msg)
            except Exception as e:
                print(f"[report_error] BOTGA XABAR YUBORISHDA XATO: {e}")
        print(f"[ERROR] {where}: {error}")

    async def create_group(self, client, title, user_to_add, session_name):
        async with self.session_locks[session_name]:
            try:
                result = await client(CreateChannelRequest(
                    title=title,
                    about="Avto-created group",
                    megagroup=True
                ))

                chat = result.chats[0]
                await client(InviteToChannelRequest(chat.id, [user_to_add]))

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
                    self.sessions[session_name]["floodwait"] = 0

                await asyncio.sleep(self.delay_seconds)

            except FloodWaitError as e:
                if session_name in self.sessions:
                    self.sessions[session_name]["floodwait"] = e.seconds
                await self.report_error("auto_create_groups FloodWait", e)
                await asyncio.sleep(e.seconds + 15)

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
                    "floodwait": 0
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
