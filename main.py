from telethon import TelegramClient, events
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import User
import asyncio
import logging
import re
import os

# === CONFIGURATION ===
# Replace these with your own values!
API_ID = 37946100
API_HASH = 'dd3ed4f7e39c1e62a0c70eb9e44aa1f5'
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

# Regex to find Telegram join links (t.me/joinchat/HASH or t.me/USERNAME or t.me/+HASH)
LINK_PATTERN = re.compile(r'https?://t\.me/(?:joinchat/|\+)?([a-zA-Z0-9_]+)')

# === HELPER FUNCTIONS ===

async def broadcast_loop():
    """Loops indefinitely, sending messages to ALL groups every X minutes."""
    global broadcast_running
    while broadcast_running:
        logger.info("📢 Starting broadcast cycle...")
        
        # 1. Get all groups dynamically (no .add needed)
        groups = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group:
                groups.append(dialog)
        
        if not groups:
            logger.warning("No groups found.")
        
        # 2. Send to all groups with delay
        for group in groups:
            if not broadcast_running:
                break
            
            try:
                if broadcast_msg:
                    await client.send_message(group.id, broadcast_msg)
                    logger.info(f"Sent to {group.title}")
                
                # "send message to all ten gcs in 20 seconds" -> ~2 seconds gap
                await asyncio.sleep(2) 
            except Exception as e:
                logger.error(f"Failed to send to {group.id}: {e}")

        # 3. Wait for the interval
        if broadcast_running:
            logger.info(f"Cycle finished. Waiting {broadcast_interval_minutes} minutes.")
            await asyncio.sleep(broadcast_interval_minutes * 60)

async def daily_pic_loop():
    """Sends the saved picture to ALL DMs every 24 hours."""
    while True:
        # Wait 24 hours
        await asyncio.sleep(24 * 60 * 60)
        
        if not daily_pic_path or not os.path.exists(daily_pic_path):
            continue
            
        logger.info("📸 Starting daily picture broadcast...")
        async for dialog in client.iter_dialogs():
            if dialog.is_user and not dialog.entity.bot and not dialog.entity.is_self:
                try:
                    await client.send_file(dialog.id, daily_pic_path, caption="Daily Update")
                    # "With 10 sec gape" (using same safety gap as .textdm)
                    await asyncio.sleep(10)
                except Exception as e:
                    pass

# === COMMANDS ===

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.alive$'))
async def alive(event):
    await event.reply("Yes I'm alive")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.auto\s+(.+)\s+(\d+)$'))
async def auto_handler(event):
    global broadcast_running, broadcast_task, broadcast_msg, broadcast_interval_minutes
    
    msg = event.pattern_match.group(1)
    minutes = int(event.pattern_match.group(2))
    
    broadcast_msg = msg
    broadcast_interval_minutes = minutes
    broadcast_running = True
    
    if broadcast_task:
        broadcast_task.cancel()
    
    broadcast_task = asyncio.create_task(broadcast_loop())
    await event.reply(f"✅ **Auto Broadcast Started**\nMsg: `{msg}`\nInterval: {minutes} mins\nGap: 2s per group")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.auto off$'))
async def auto_stop(event):
    global broadcast_running, broadcast_task
    broadcast_running = False
    if broadcast_task:
        broadcast_task.cancel()
    await event.reply("🛑 Auto broadcast stopped.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.pic$'))
async def set_pic(event):
    global daily_pic_path, daily_pic_task
    
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.reply("❌ Reply to an image with `.pic` to set it.")
        return
        
    path = await reply.download_media()
    daily_pic_path = path
    
    if not daily_pic_task:
        daily_pic_task = asyncio.create_task(daily_pic_loop())
        
    await event.reply("✅ Daily picture set! Will be sent to all DMs every 24h.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.textdm\s+(.+)$'))
async def textdm(event):
    text = event.pattern_match.group(1)
    await event.reply("🚀 Starting DM broadcast (10s gap)...")
    
    sent_count = 0
    skipped_count = 0
    
    async for dialog in client.iter_dialogs():
        if dialog.is_user and not dialog.entity.bot and not dialog.entity.is_self:
            if dialog.id == event.chat_id:
                skipped_count += 1  # skip the chat where the command was triggered
                continue
            try:
                await client.send_message(dialog.id, text)
                sent_count += 1
                await asyncio.sleep(10)  # "With 10 sec gap"
            except Exception as e:
                logger.error(f"Failed DM to {dialog.id}: {e}")
                
    await event.reply(f"✅ DM Broadcast done.\nSent: {sent_count} users\nSkipped: {skipped_count} (your chat)")
    # === AUTO-JOIN & AUTO-REPLY ===

@client.on(events.NewMessage)
async def global_listener(event):
    # 1. Auto-Join Logic (Checks ALL messages)
    text = event.raw_text or ""
    links = LINK_PATTERN.findall(text)
    
    for link_suffix in links:
        # Run in background to not block
        asyncio.create_task(join_group(link_suffix))

    # 2. Auto-Reply Logic (Incoming DMs)
    # "whenever someone texts... Reply everyone"
    if event.is_private and event.incoming:
        sender = await event.get_sender()
        if isinstance(sender, User) and not sender.bot:
            # Only reply if auto broadcast is running (reusing the 'auto' message?)
            if broadcast_msg:
                 # Small delay to look human
                await asyncio.sleep(2)
                await event.reply(broadcast_msg)

async def join_group(suffix):
    try:
        if suffix.startswith('+') or len(suffix) > 15:
            # Private invite hash
            hash_val = suffix.replace('+', '')
            await client(ImportChatInviteRequest(hash_val))
            logger.info(f"Joined private chat: {hash_val}")
        else:
            # Public username
            await client(JoinChannelRequest(suffix))
            logger.info(f"Joined public chat: {suffix}")
    except Exception as e:
        logger.error(f"Failed to join {suffix}: {e}")

# === RUN ===
print("Userbot is running...")
client.start()
client.run_until_disconnected()
