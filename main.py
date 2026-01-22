from telethon import TelegramClient, events
from telethon.tl.types import User
import asyncio
import logging
import os

# === CONFIGURATION ===
API_ID = 31782182
API_HASH = 'ddcbe9f7d3afb5498db6098897ff8376'
SESSION_NAME = 'userbot_earn_session'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# === STATE ===
broadcast_running = False
broadcast_task = None
broadcast_msg = None
broadcast_interval_minutes = 30

daily_pic_path = None
daily_pic_task = None

# DM Broadcast state
textdm_running = False
excluded_users = set()

# Tracking replied users for auto-reply logic
replied_users = set()

# Auto-reply message
CHANNEL_INVITE_MSG = """⚠️NO FREE PIC AND VIDEO ⚠️       
🎀🎀🎀🎀🎀🎀🎀🎀🎀🎀
Age 15✅

No real meet✅

✅ 50₹ ---- 𝟓 𝐧𝐮𝐝𝐞 𝐩𝐢𝐜
✅50₹ ---- 𝐃𝐞𝐦𝐨 (10sec Nude 𝐯𝐢𝐝𝐞𝐨 𝐜𝐚𝐥𝐥)

✅100₹ ---- 𝟓 𝐦𝐢𝐧 (𝐅𝐮𝐥𝐥 𝐧𝐮𝐝𝐞 𝐯𝐢𝐝𝐞𝐨 𝐜𝐚𝐥𝐥)
🥵 150₹ ---- 𝟏𝟎 𝐦𝐢𝐧 (𝐅𝐮𝐥𝐥 𝐧𝐮𝐝𝐞 𝐯𝐢𝐝𝐞𝐨 𝐜𝐚𝐥𝐥)
😀 200₹ ---- 𝟏𝟓 𝐦𝐢𝐧 (𝐅𝐮𝐥𝐥 𝐧𝐮𝐝𝐞 𝐯𝐢𝐝𝐞𝐨 𝐜𝐚𝐥𝐥)
💬 250₹ ---- 𝟐𝟎 𝐦𝐢𝐧 (𝐅𝐮𝐥𝐥 𝐧𝐮𝐝𝐞 𝐯𝐢𝐝𝐞𝐨 𝐜𝐚𝐥𝐥)

✅ 250₹ ---- 𝟏 𝐡𝐨𝐮 𝐕𝐨𝐢𝐜𝐞 𝐜𝐚𝐥𝐥𝐢𝐧𝐠 (𝐅𝐮𝐥𝐥 𝐬𝐞𝐱𝐲 𝐭𝐚𝐥𝐤)
✔ 150₹ ---- 2𝟎 𝐦𝐢𝐧 𝐬𝐞𝐱 𝐜𝐡𝐚𝐭 𝐚𝐧𝐝 𝐧𝐮𝐝𝐞 𝐩𝐢𝐜𝐬 
😀 100₹ ---- 10 𝐦𝐢𝐧 (𝐅𝐮𝐥𝐥 𝐧𝐮𝐝𝐞 Fingering 𝐯𝐢𝐝𝐞𝐨)  🌹💋"""

# === HELPERS ===

async def broadcast_loop():
    global broadcast_running
    while broadcast_running:
        logger.info("📢 Starting broadcast cycle...")
        groups = []

        async for dialog in client.iter_dialogs():
            if dialog.is_group:
                groups.append(dialog)

        for group in groups:
            if not broadcast_running:
                break
            try:
                if broadcast_msg:
                    await client.send_message(group.id, broadcast_msg)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Failed to send to {group.id}: {e}")

        await asyncio.sleep(broadcast_interval_minutes * 60)

async def daily_pic_loop():
    while True:
        await asyncio.sleep(24 * 60 * 60)
        if not daily_pic_path or not os.path.exists(daily_pic_path):
            continue

        async for dialog in client.iter_dialogs():
            if dialog.is_user and not dialog.entity.bot and not dialog.entity.is_self:
                try:
                    await client.send_file(dialog.id, daily_pic_path, caption="Daily Update")
                    await asyncio.sleep(10)
                except Exception:
                    pass

# === COMMANDS ===

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.alive$'))
async def alive(event):
    await event.reply("Yes I'm alive")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.auto\s+(.+)\s+(\d+)$'))
async def auto_handler(event):
    global broadcast_running, broadcast_task, broadcast_msg, broadcast_interval_minutes

    broadcast_msg = event.pattern_match.group(1)
    broadcast_interval_minutes = int(event.pattern_match.group(2))
    broadcast_running = True

    if broadcast_task:
        broadcast_task.cancel()

    broadcast_task = asyncio.create_task(broadcast_loop())
    await event.reply("✅ Auto broadcast started")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.auto off$'))
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.sauto$'))
async def auto_stop(event):
    global broadcast_running, broadcast_task
    broadcast_running = False
    if broadcast_task:
        broadcast_task.cancel()
    await event.reply("🛑 Auto broadcast stopped")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.pic$'))
async def set_pic(event):
    global daily_pic_path, daily_pic_task
    reply = await event.get_reply_message()

    if not reply or not reply.media:
        await event.reply("❌ Reply to an image")
        return

    daily_pic_path = await reply.download_media()
    if not daily_pic_task:
        daily_pic_task = asyncio.create_task(daily_pic_loop())

    await event.reply("✅ Daily pic set")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.textdm\s+(.+)$'))
async def textdm(event):
    global textdm_running
    textdm_running = True
    text = event.pattern_match.group(1)
    count = 0

    async for dialog in client.iter_dialogs():
        if not textdm_running:
            break

        if dialog.is_user and not dialog.entity.bot and not dialog.entity.is_self:
            if dialog.id in excluded_users:
                continue
            try:
                await client.send_message(dialog.id, text)
                count += 1
                await asyncio.sleep(10)
            except Exception:
                pass

    textdm_running = False
    await event.reply(f"✅ Sent to {count} users")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.stextdm$'))
async def stop_textdm(event):
    global textdm_running
    textdm_running = False
    await event.reply("🛑 DM broadcast stopped")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.r$'))
async def exclude_user(event):
    if not event.is_private:
        return
    excluded_users.add(event.chat_id)
    await event.reply("✅ User excluded")

# === AUTO-REPLY ONLY (NO AUTO JOIN) ===

@client.on(events.NewMessage())
async def global_listener(event):
    if event.is_private and not event.out and broadcast_running:
        sender = await event.get_sender()
        if isinstance(sender, User) and not sender.bot:
            if sender.id not in replied_users:
                replied_users.add(sender.id)
                await asyncio.sleep(2)
                await event.reply(CHANNEL_INVITE_MSG)

# === RUN ===
print("Userbot is running...")
client.start()
client.run_until_disconnected()
