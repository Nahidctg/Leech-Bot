# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 13.0 - Final Ultra) ---
# --- ফিচার: স্মার্ট ডিকোড, ৪জিবি হাইব্রিড, ৫ সেকেন্ড ফ্লাড প্রোটেকশন ---
# --- বিশেষ আপডেট: প্রিমিয়াম ভিজ্যুয়াল প্রগ্রেস বার (Speed + ETA + Blocks) ---
# --- বিশেষ সাপোর্ট: Kraken, Vidara, Flash-Files, Fredl, Terabox (All In) ---
# ==============================================================================

import os
import time
import asyncio
import subprocess
import shutil
import re
import requests
import yt_dlp
import logging
from datetime import datetime
from urllib.parse import urlparse
from pyrogram import Client, filters, idle, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# লগার সেটআপ (ডিটেইলড লগ দেখার জন্য)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন (Config) ---
# ==============================================================================

API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# ৪জিবি সাপোর্টের জন্য প্রিমিয়াম সেশন (না থাকলে "" রাখুন)
STRING_SESSION = "" 
LOG_CHANNEL = -1002491365982 

# ক্লায়েন্ট সেটআপ
app = Client(
    "bot_instance", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    workers=100
)

user_app = None
if STRING_SESSION and len(STRING_SESSION) > 10:
    user_app = Client(
        "premium_account", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

# ইউজারের ডাউনলোড ডেটা স্টোর
user_data = {}

# ==============================================================================
# --- ২. ইউটিলিটি ফাংশন (Formatting & Helpers) ---
# ==============================================================================

def human_size(num):
    """বাইটকে রিডেবল ফরম্যাটে রূপান্তর (KB, MB, GB)"""
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

def time_formatter(seconds):
    """সেকেন্ডকে সুন্দর সময় ফরম্যাটে রূপান্তর (h m s)"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return ((f"{hours}h " if hours else "") + (f"{minutes}m " if minutes else "") + f"{seconds}s")

def get_duration(file_path):
    """ভিডিও ফাইলের ডিউরেশন বের করা"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except: return 0

# ==============================================================================
# --- ৩. আলটিমেট প্রগ্রেস বার (৫ সেকেন্ড আপডেট + প্রিমিয়াম ডিজাইন) ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, start_time, last_update_time):
    now = time.time()
    # ৫ সেকেন্ড পর পর আপডেট হবে যাতে টেলিগ্রাম লিমিট না খায়
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    elapsed_time = now - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    percentage = (current * 100) / total if total > 0 else 0
    
    # ইটিএ (বাকি সময়)
    remaining_bytes = total - current
    eta = remaining_bytes / speed if speed > 0 else 0
    
    # আধুনিক ব্লক বার ডিজাইন
    bar_length = 12
    filled_length = int(percentage / (100 / bar_length))
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    # সম্পূর্ণ প্রফেশনাল ইউআই
    progress_ui = (
        f"**┏━━━━━━━━━━━━━━━━━━━┓**\n"
        f"**┃ ⚡ {status_text}**\n"
        f"**┣━━━━━━━━━━━━━━━━━━━┛**\n"
        f"**┃ 🌀 [{bar}] {round(percentage, 2)}%**\n"
        f"**┃ 🚀 গতি: `{human_size(speed)}/s`**\n"
        f"**┃ 📦 সাইজ: `{human_size(current)}` / `{human_size(total)}`**\n"
        f"**┃ ⏳ বাকি সময়: `{time_formatter(eta)}`**\n"
        f"**┗━━━━━━━━━━━━━━━━━━━┛**"
    )

    try:
        await status_msg.edit_text(progress_ui)
    except Exception as e:
        logger.error(f"UI Update Error: {e}")

# ==============================================================================
# --- ৪. স্মার্ট লিঙ্ক রেজলভার (Decoder + Bypass) ---
# ==============================================================================

def get_smart_link(url):
    """রিডাইরেক্ট এবং ডাইরেক্ট লিঙ্ক চেক করার ইঞ্জিন"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': url
    }
    try:
        session = requests.Session()
        res = session.get(url, allow_redirects=True, timeout=12, stream=True)
        final_url = res.url
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov']):
            return final_url
        url = final_url
    except: pass

    # YT-DLP স্ক্যান
    ydl_opts = {'quiet': True, 'format': 'best', 'noplaylist': True, 'nocheckcertificate': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('url', url)
        except: return url

# ==============================================================================
# --- ৫. মূল হ্যান্ডলারসমূহ (The System Core) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    await message.reply_text(
        f"**বট অনলাইন! 🚀 (V 13.0 - Ultra Speed)**\n\n"
        f"যেকোনো লিঙ্ক পাঠান, আমি সুপার-ফাস্ট ডাউনলোড করে দিব।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n"
        f"**প্রগ্রেস আপডেট:** `প্রতি ৫ সেকেন্ড`"
    )

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    loop = asyncio.get_event_loop()
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # ডিকোড করা
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে সুপার-ফাস্ট ডাউনলোড শুরু হচ্ছে... 📥")
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)
    
    start_time = time.time()
    last_update_time = [0]

    try:
        # ডাউনলোড প্রগ্রেস হুক
        def ydl_progress_hook(d):
            if d['status'] == 'downloading':
                current = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                asyncio.run_coroutine_threadsafe(
                    progress_bar(current, total, "ডাউনলোড হচ্ছে...", status_msg, start_time, last_update_time),
                    loop
                )

        ydl_opts = {
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'progress_hooks': [ydl_progress_hook],
            'external_downloader': 'aria2c', 
            'external_downloader_args': ['--max-connection-per-server=16', '--split=16', '-x16'],
            'nocheckcertificate': True, 'quiet': True, 'no_warnings': True
        }
        
        # থ্রেডে রান করা যাতে বট হ্যাং না হয়
        await asyncio.to_thread(yt_dlp.YoutubeDL(ydl_opts).download, [url])
        
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ইনভ্যালিড।")
            return
        
        file_path = max(files, key=os.path.getctime)
        user_data[user_id] = {
            "file_path": file_path, 
            "new_name": os.path.basename(file_path),
            "thumb": None, 
            "dir": download_dir
        }

        await status_msg.delete()
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n📄 `{os.path.basename(file_path)}` \n💰 `{human_size(os.path.getsize(file_path))}`\n\nএখন নাম বা থাম্বনেইল সেট করে আপলোড দিন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ ডাউনলোড এরর: {str(e)}")

# --- রিনেম ও থাম্বনেইল হ্যান্ডলার ---

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_data: return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 ফাইল নেম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট হয়েছে!")

# ==============================================================================
# --- ৬. আপলোড সেকশন (Hybrid 4GB Support) ---
# ==============================================================================

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data: return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    ext = os.path.splitext(old_path)[1]
    final_name = data["new_name"] if data["new_name"].endswith(ext) else data["new_name"] + ext
    new_path = os.path.join(os.path.dirname(old_path), final_name)
    os.rename(old_path, new_path)
    
    status_msg = await callback_query.message.edit_text("📤 আপলোড প্রস্তুতি চলছে...")
    start_time = time.time()
    last_update_time = [0]

    async def upload_progress(current, total):
        await progress_bar(current, total, "আপলোড হচ্ছে...", status_msg, start_time, last_update_time)

    try:
        file_size = os.path.getsize(new_path)
        duration = get_duration(new_path)
        
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, 
                video=new_path, 
                duration=duration,
                thumb=data["thumb"], 
                caption=f"✅ `{final_name}`", 
                progress=upload_progress
            )
            # চ্যানেল থেকে কপি
            await app.copy_message(
                chat_id=user_id, 
                from_chat_id=LOG_CHANNEL, 
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{final_name}`\n💰 `{human_size(file_size)}`"
            )
        else:
            if file_size > 2000*1024*1024:
                return await status_msg.edit_text("❌ সেশন ছাড়া ২জিবির বড় ফাইল সম্ভব নয়।")
            await app.send_video(
                chat_id=user_id, 
                video=new_path, 
                duration=duration, 
                thumb=data["thumb"], 
                caption=f"✅ `{final_name}`", 
                progress=upload_progress
            )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        shutil.rmtree(data["dir"], ignore_errors=True)
        if user_id in user_data: del user_data[user_id]

# ==============================================================================
# --- ৭. সিস্টেম রানার (The Engine Runner) ---
# ==============================================================================

async def start_services():
    print("-" * 40)
    await app.start()
    print("মূল বট ক্লায়েন্ট অনলাইন! ✅")
    
    if user_app:
        try:
            await user_app.start()
            print("প্রিমিয়াম ইউজার সেশন অনলাইন! ✅")
        except Exception as e:
            print(f"সেশন এরর: {e}")
    
    print("বট এখন পুরোপুরি প্রস্তুত! 🚀")
    print("-" * 40)
    await idle()
    await app.stop()
    if user_app: await user_app.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        print("সিস্টেম বন্ধ করা হয়েছে।")
