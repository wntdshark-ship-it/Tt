import asyncio
import time
import os
from datetime import date
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import (
    GetParticipantRequest,
    GetFullChannelRequest
)
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

# ================= FAKE TEST CONFIG =================

API_ID = 39886693
API_HASH = "ef44c10853510943fe68611109ccfd3f"
BOT_TOKEN = "8289114029:AAEJ4gkDj1AqmMwwDBDrYEpqC6hvyQQdDTA"

USER_SESSION = (
    "1BVtsOKEBuwPIRhss56oDmrjnq03wUbTSnH3TGOq7l-IgoKou4JpdQ7zMwpKbQIXUHlY8"
    "RP0dr6Z8qoYQjtJlnzKNa0tZeD6q8vFh2K38cO9mmN2vNjj94INXqcj-QjPsOxd1nvS9R"
    "C-gewUSgt-ds_-dynkttUkoD_kleGsVVKqtGDlonU1wa4JNKNlxlBUaZEQnhPpikg6OK"
    "f28przT_T_eahXovasvIDLmm3bUYkSUIW38q66VrhJl9t2bTlV15f7Af2e5kbGzatpX"
    "K0LQ3U1I-zOyr58spwKbKtq0ZWOe-r2zqP2Y14p3klRhZqvIrX6K6JIt1oGiCfAqhbX"
    "UmbFmRx2e7k8="
)

PROCESSING_CHANNEL_ID = -1003041662927
MIN_MEMBERS = 10

USE_ME_CHANNEL = "https://t.me/TruecallerBySmith"

# ====================================================

bot = TelegramClient("bot", API_ID, API_HASH)
user = TelegramClient(StringSession(USER_SESSION), API_ID, API_HASH)

LAST_REQUEST = {}  # group_chat_id -> user_id

# ================= BUTTON =================

def use_me_button():
    return [[Button.url("▶ USE ME HERE", USE_ME_CHANNEL)]]

# ================= START / HELP =================

@bot.on(events.NewMessage(pattern=r'^/(start|help)$'))
async def start_help(event):
    await event.reply(
        "Welcome User!\n\n"
        "Use commands in group.\n"
        "For updates & usage click below 👇",
        buttons=use_me_button()
    )

# ================= ADMIN CHECK =================

async def bot_is_admin(event):
    try:
        me = await bot.get_me()
        p = await bot(GetParticipantRequest(event.chat_id, me.id))
        return isinstance(
            p.participant,
            (ChannelParticipantAdmin, ChannelParticipantCreator)
        )
    except:
        return False

# ================= MEMBER COUNT =================

async def group_member_count(event):
    try:
        entity = await bot.get_entity(event.chat_id)
        if getattr(entity, "megagroup", False):
            full = await bot(GetFullChannelRequest(entity))
            return full.full_chat.participants_count
        else:
            full = await bot(GetFullChatRequest(event.chat_id))
            return full.full_chat.participants_count
    except:
        return 0

# ================= COMMAND HANDLER =================

@bot.on(events.NewMessage(pattern=r'^/'))
async def command_handler(event):
    if not event.is_group:
        return
    if not await bot_is_admin(event):
        return
    if await group_member_count(event) < MIN_MEMBERS:
        return

    LAST_REQUEST[event.chat_id] = event.sender_id

    # USER account sends command
    await user.send_message(PROCESSING_CHANNEL_ID, event.raw_text)
    await event.reply("⏳ Processing...")

# ================= RESPONSE LISTENER (FIXED) =================

@user.on(events.NewMessage(chats=PROCESSING_CHANNEL_ID))
async def response_listener(event):
    if not event.text:
        return
    if not LAST_REQUEST:
        return

    text = event.text.lower()

    # ❌ IGNORE STATUS MESSAGES
    ignore_words = ["processing", "wait", "fetch", "loading", "searching"]
    if any(word in text for word in ignore_words):
        return

    # ✅ ACCEPT ONLY FINAL DATA (JSON / CODE FORMAT)
    is_json = "{" in event.text and "}" in event.text
    is_code = "```" in event.text or event.text.count("\n") > 5

    if not (is_json or is_code):
        return  # not final result

    group_chat_id, _ = LAST_REQUEST.popitem()

    filename = f"BotBySmith_{int(time.time())}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(event.text)

    await bot.send_file(
        group_chat_id,
        filename,
        caption="✅ Result",
        buttons=use_me_button()
    )

    os.remove(filename)

# ================= START =================

async def main():
    await user.start()
    await bot.start(bot_token=BOT_TOKEN)
    await asyncio.gather(
        bot.run_until_disconnected(),
        user.run_until_disconnected()
    )

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
