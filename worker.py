# worker.py
import asyncio
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest, InviteToChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatAdminRights
from telethon.errors import FloodWaitError

import os
from telethon import TelegramClient

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

class UserbotWorker:
    def __init__(self, session_name, api_id, api_hash, group_title, user_to_add, start_index=None):
        self.session_name = session_name
        self.api_id = api_id
        self.api_hash = api_hash
        self.group_title = group_title
        self.user_to_add = user_to_add
        self.running = False
        self.data_file = f"{self.session_name}_data.txt"
        self.floodwait_seconds = 0
        self.task = None

        # ✅ MUHIM QATOR:
        self.session_path = os.path.join(SESSIONS_DIR, session_name)
        self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)

        # ✅ indeksni saqlash
        self.index = self.load_index()
        if start_index is not None:
            self.index = start_index
            self.save_index()


    def load_index(self):
        try:
            with open(self.data_file, 'r') as f:
                first_line = f.readline()
                return int(first_line.strip())
        except FileNotFoundError:
            return 1

    def save_index(self):
        lines = []
        try:
            with open(self.data_file, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            pass

        lines = [f"{self.index}\n"] + lines[1:]
        with open(self.data_file, 'w') as f:
            f.writelines(lines)

    def append_log(self, link):
        with open(self.data_file, 'a') as f:
            f.write(f"{link} {self.user_to_add}\n")

    async def start(self):
        self.running = True
        await self.client.start()
        print(f"✅ [{self.session_name}] Ulandi.")
        self.task = asyncio.create_task(self._runner())

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        await self.client.disconnect()
        print(f"🛑 [{self.session_name}] To‘xtadi.")

    async def _runner(self):
        while self.running:
            try:
                await self.create_group()
                await asyncio.sleep(5)
            except FloodWaitError as e:
                self.floodwait_seconds = e.seconds
                print(f"⚠️ [{self.session_name}] FloodWait: {e.seconds}s")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"❌ [{self.session_name}] Xatolik: {e}")
                await asyncio.sleep(5)

    async def create_group(self):
        group_title_full = f"{self.group_title} {self.index}"

        result = await self.client(CreateChannelRequest(
            title=group_title_full,
            about="Bot orqali yaratilgan",
            megagroup=True
        ))

        chat = result.chats[0]
        try:
            invite = await self.client(ExportChatInviteRequest(chat.id))
            link = invite.link
        except Exception:
            link = "No link"

        try:
            await self.client(InviteToChannelRequest(chat.id, [self.user_to_add]))
            await self.client(EditAdminRequest(chat.id, self.user_to_add, ChatAdminRights(
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=True,
                anonymous=True,
                manage_call=True,
                manage_topics=True,
                other=True
            ), rank="Admin"))
        except Exception as e:
            print(f"❌ Admin/Invite xato: {e}")

        await self.client.send_message(chat.id, f"Guruh yaratildi: {group_title_full}\nLink: {link}")

        # ✅ Faylga yozish
        self.append_log(link)
        self.index += 1
        self.save_index()

        print(f"✅ [{self.session_name}] Guruh yaratildi: {link}")

    def get_status(self):
        if self.running:
            return f"🟢 {self.session_name}: Ishlayapti. FloodWait={self.floodwait_seconds}s, Next index={self.index}"
        else:
            return f"🔴 {self.session_name}: To‘xtagan."

