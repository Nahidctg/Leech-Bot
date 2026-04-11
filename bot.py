# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 12.0 - Final Ultra Detailed) ---
# --- ফিচার: স্মার্ট ডিকোড ইঞ্জিন, ৪জিবি হাইব্রিড সাপোর্ট, ফ্লাড প্রোটেকশন (১০ সেকেন্ড) ---
# --- বিশেষ আপডেট: Aria2 + YT-DLP Multi-thread Speed Booster (100% Fast) ---
# --- বিশেষ সাপোর্ট: Kraken, Vidara, Flash-Files, Fredl, Terabox (All Features In) ---
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
from urllib.parse import urlparse
from pyrogram import Client, filters, idle, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# লগার সেটআপ (বিস্তারিত লগ দেখার জন্য)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন (Config - Original Detailed Structure) ---
# ==============================================================================

API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# --- ৪জিবি সাপোর্টের জন্য প্রিমিয়াম সেশন ---
# সেশন না থাকলে শুধু "" রাখুন। বট ২জিবি মোডে অনায়াসেই চলবে।
STRING_SESSION = "" 
# লগ চ্যানেল আইডি (সেশন দিলে অবশ্যই সঠিক আইডি দিন)
LOG_CHANNEL = -1002491365982 

# ক্লায়েন্ট সেটআপ (বট এবং সেশন)
app = Client(
    "interactive_bot_instance", 
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
# --- ২. কোর ইউটিলিটি ফাংশনসমূহ (Helpers - No Change) ---
# ==============================================================================

def human_size(num):
    """বাইটকে রিডেবল ফরম্যাটে রূপান্তর করে (KB, MB, GB)"""
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

def get_duration(file_path):
    """ভিডিও ফাইলের ডিউরেশন বা সঠিক সময় বের করে।"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception as e:
        logger.error(f"ডিউরেশন এক্সট্রাকশন এরর: {e}")
    return 0

# ==============================================================================
# --- ৩. স্মার্ট প্রগ্রেস বার (১০ সেকেন্ড ফ্লাড প্রোটেকশন সিস্টেম) ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    """
    ১০ সেকেন্ড পর পর প্রগ্রেস আপডেট করবে যাতে টেলিগ্রাম ফ্লাড বা হ্যাং না হয়।
    """
    now = time.time()
    if (now - last_update_time[0]) < 10:
        return
    last_update_time[0] = now

    percentage = (current * 100) / total if total > 0 else 0
    bar_length = 10
    filled_length = int(percentage // 10)
    bar = "▰" * filled_length + "▱" * (bar_length - filled_length)
    
    try:
        # প্রগ্রেস বারটি এডিট করে ইউজারকে তথ্য দেওয়া
        await status_msg.edit_text(
            f"**{status_text}**\n\n"
            f"🌀 {bar} **{round(percentage, 2)}%**\n"
            f"📦 সাইজ: `{human_size(current)}` / `{human_size(total)}`"
        )
    except Exception as e:
        logger.error(f"প্রগ্রেস বার আপডেট এরর: {e}")

# ==============================================================================
# --- ৪. স্মার্ট লিঙ্ক রেজলভার ENGINE (Ultra Decoder + Speed Bypass) ---
# ==============================================================================

def get_smart_link(url):
    """
    এটি রিডাইরেক্ট, ক্লাউডফ্লেয়ার বাইপাস এবং স্মার্ট লিঙ্ক ফিক্স করে।
    """
    print(f"DEBUG: এনালাইসিস শুরু হচ্ছে - {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': url
    }

    # ১. সরাসরি ফাইল লিঙ্ক চেক
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, allow_redirects=True, timeout=12, stream=True)
        final_url = response.url
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi']):
            return final_url
        url = final_url
    except Exception as e:
        print(f"Redirect Engine Error: {e}")

    # ২. YT-DLP স্ক্যান
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'format': 'best',
        'noplaylist': True, 'nocheckcertificate': True,
        'extractor_args': {'generic': ['impersonate']},
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('url', url)
        except:
            return url

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ (The Main Core System) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    print(f"DEBUG: Start কমান্ড দিয়েছেন: {message.from_user.id}")
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    
    await message.reply_text(
        f"**বট অনলাইন! 🚀 (Version 12.0 - Ultra Speed Enabled)**\n\n"
        f"এখন Kraken, Vidara সহ যেকোনো লিঙ্ক সুপার-ফাস্ট গতিতে ডাউনলোড হবে।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n\n"
        f"যেকোনো ভিডিও লিঙ্ক পাঠান। প্রগ্রেস ১০ সেকেন্ড পর পর আপডেট হবে।"
    )

# --- ৬. ডাউনলোড সেকশন (Aria2 + YT-DLP Multi-thread Speed Booster) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    loop = asyncio.get_event_loop()
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # লিঙ্ক ডিকোড করা
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে সুপার-ফাস্ট ডাউনলোড শুরু হচ্ছে... 📥")
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)
    last_update_time = [0]

    try:
        # ১. Aria2 চেষ্টা (ডিরেক্ট লিঙ্কের জন্য)
        is_protected = any(x in url for x in ["kraken", "vidara", "flash-files", "fredl", "terabox", "frdl"])
        
        if not is_protected:
            cmd = ["aria2c", "--dir", download_dir, "--max-connection-per-server=16", "--split=16", direct_link]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
            while True:
                line = await process.stdout.readline()
                if not line: break
                match = re.search(r'\((\d+)%\)', line.decode())
                if match:
                    await progress_bar(int(match.group(1)), 100, "📥 High Speed Download...", status_msg, last_update_time)
            await process.wait()

        # ২. YT-DLP + Aria2 এক্সটার্নাল স্পিড বুস্টার (হ্যাং ইস্যু ফিক্সড)
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("অ্যাডভান্সড ইঞ্জিন ব্যবহার করে সুপার স্পিডে ডাউনলোড হচ্ছে... 🔄")
            
            def ydl_progress_hook(d):
                if d['status'] == 'downloading':
                    current = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                    # ইভেন্ট লুপে প্রগ্রেস পাঠানো (থ্রেড সেফ)
                    asyncio.run_coroutine_threadsafe(
                        progress_bar(current, total, "📥 Ultra Speed Download...", status_msg, last_update_time),
                        loop
                    )

            ydl_opts = {
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'progress_hooks': [ydl_progress_hook],
                'extractor_args': {'generic': ['impersonate']},
                'external_downloader': 'aria2c', # স্পিড বাড়ানোর জন্য Aria2 ব্যবহার
                'external_downloader_args': ['--max-connection-per-server=16', '--split=16'],
                'nocheckcertificate': True, 'quiet': True
            }
            # থ্রেডে রান করা যাতে বট হ্যাং না হয়
            await asyncio.to_thread(yt_dlp.YoutubeDL(ydl_opts).download, [url])
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]

        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ইনভ্যালিড অথবা প্রটেক্টেড।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # অরিজিনাল ইউজার ডেটা স্টোর ফিচার
        user_data[user_id] = {
            "file_path": file_path, "new_name": os.path.basename(file_path),
            "thumb": None, "dir": download_dir
        }

        await status_msg.delete()
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n📄 `{os.path.basename(file_path)}` \n💰 `{human_size(file_size)}` \n\nনাম বা থাম্বনেইল সেট করে আপলোড শুরু করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ ডাউনলোড এরর: {str(e)}")

# --- ৭. রিনেম ও থাম্বনেইল হ্যান্ডলার (অরিজিনাল ফিচার) ---

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

# --- ৮. আপলোড সেকশন (Hybrid 4GB Support + Copy Message Logic) ---

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
    last_update_time = [0]

    async def upload_progress(current, total):
        await progress_bar(current, total, "📤 ফাইল আপলোড হচ্ছে...", status_msg, last_update_time)

    try:
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, video=new_path, duration=get_duration(new_path),
                thumb=data["thumb"], caption=f"✅ `{final_name}`", progress=upload_progress
            )
            # চ্যানেল থেকে ইউজারের কাছে কপি করা (Original Logic)
            await app.copy_message(chat_id=user_id, from_chat_id=LOG_CHANNEL, message_id=sent_msg.id,
                                   caption=f"✅ **ফাইল:** `{final_name}`\n💰 {human_size(os.path.getsize(new_path))}")
        else:
            if os.path.getsize(new_path) > 2000*1024*1024:
                return await status_msg.edit_text("❌ সেশন ছাড়া ২জিবির বড় ফাইল সম্ভব নয়।")
            await app.send_video(chat_id=user_id, video=new_path, duration=get_duration(new_path), 
                                 thumb=data["thumb"], caption=f"✅ `{final_name}`", progress=upload_progress)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        shutil.rmtree(data["dir"], ignore_errors=True)
        del user_data[user_id]

# ==============================================================================
# --- ৯. সিস্টেম রানার সেকশন (Final Detailed Runner) ---
# ==============================================================================

async def start_services():
    print("-" * 40)
    print("সার্ভার সিস্টেম চালু হচ্ছে... (Version 12.0)")
    await app.start()
    print("মূল বট ক্লায়েন্ট স্টার্ট হয়েছে! ✅")
    
    if user_app:
        try:
            await user_app.start()
            print("প্রিমিয়াম ইউজার ক্লায়েন্ট স্টার্ট হয়েছে! ✅")
        except Exception as e:
            print(f"সেশন ফেইল: {e}")
    
    print("বট এখন পুরোপুরি অনলাইন এবং রেসপন্স করার জন্য প্রস্তুত! 🚀")
    print("-" * 40)
    await idle()
    await app.stop()
    if user_app: await user_app.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        print("বট বন্ধ করা হয়েছে।")
