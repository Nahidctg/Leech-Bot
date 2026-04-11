# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 10.0 - Final Ultimate) ---
# --- ফিচার: স্মার্ট ডিকোড ইঞ্জিন, ৪জিবি হাইব্রিড সাপোর্ট, ফ্লাড প্রোটেকশন ---
# --- বিশেষ সাপোর্ট: Kraken, Vidara, Flash-Files, Fredl, Terabox (100% Fix) ---
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

# লগার সেটআপ (ডিটেইলড লগ দেখার জন্য)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন (Config - Original Detailed) ---
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
# --- ৩. স্মার্ট প্রগ্রেস বার (১০ সেকেন্ড ফ্লাড প্রোটেকশন + থ্রেড সেফ) ---
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
        # প্রগ্রেস বারটি এডিট করে ইউজারকে রিয়েল টাইম তথ্য দেওয়া
        await status_msg.edit_text(
            f"**{status_text}**\n\n"
            f"🌀 {bar} **{round(percentage, 2)}%**\n"
            f"📦 সাইজ: `{human_size(current)}` / `{human_size(total)}`"
        )
    except Exception as e:
        logger.error(f"প্রগ্রেস বার আপডেট এরর: {e}")

# ==============================================================================
# --- ৪. স্মার্ট লিঙ্ক রেজলভার ENGINE (Ultra Decoder + Bypass) ---
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

    # ১. রিডাইরেক্ট এবং সরাসরি ফাইল চেক
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, allow_redirects=True, timeout=12, stream=True)
        final_url = response.url
        
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.mp3']):
            print(f"সরাসরি ফাইল লিঙ্ক পাওয়া গেছে: {final_url}")
            return final_url
        url = final_url
    except Exception as e:
        print(f"Redirect Analysis Error: {e}")

    # ২. YT-DLP অ্যাডভান্সড স্ক্যান (Kraken, Vidara, Flash-Files এর জন্য)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'noplaylist': True,
        'user_agent': headers['User-Agent'],
        'nocheckcertificate': True,
        'extractor_args': {'generic': ['impersonate']}, # Cloudflare Bypass
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            smart_url = info.get('url', url)
            print(f"Smart Engine লিঙ্ক খুঁজে পেয়েছে: {smart_url}")
            return smart_url
        except Exception as e:
            print(f"YT-DLP Engine Error: {e}")
            return url

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ (The Core System) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    """বট স্টার্ট হ্যান্ডলার (Detailed Response)"""
    print(f"DEBUG: Start কমান্ড দিয়েছেন: {message.from_user.id}")
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    
    await message.reply_text(
        f"**বট অনলাইন এবং ১০০% রেসপন্স করার জন্য প্রস্তুত! 🚀**\n\n"
        f"এখন যেকোনো লিঙ্ক (Kraken, Vidara, Terabox, Flash-Files সহ) পাঠান।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n\n"
        f"যেকোনো মুভি বা ভিডিও লিঙ্ক পাঠান। প্রতিটি ধাপে প্রগ্রেস বার দেখতে পাবেন।"
    )

# --- ৬. ডাউনলোড সেকশন (Aria2 + YT-DLP Master Logic) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """লিঙ্ক পাওয়ার পর অটো-বাইপাস এবং ডাউনলোড প্রসেস।"""
    url = message.text.strip()
    user_id = message.from_user.id
    
    # বর্তমান ইভেন্ট লুপ সেভ করা (থ্রেড ফিক্সের জন্য অত্যন্ত জরুরি)
    loop = asyncio.get_event_loop()
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # বাইপাস ইঞ্জিন কল
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে হাই-স্পিড ডাউনলোড প্রস্তুতি চলছে... 📥")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    last_update_time = [0]

    try:
        # ১. Aria2 চেষ্টা (যদি প্রটেক্টেড সাইট না হয়)
        is_stream_site = any(x in url for x in ["kraken", "vidara", "flash-files", "fredl", "terabox", "frdl"])
        
        if not is_stream_site:
            await status_msg.edit_text("Aria2 ইঞ্জিন দিয়ে ডাউনলোড হচ্ছে... 📥")
            cmd = [
                "aria2c", "--dir", download_dir, "--max-connection-per-server=16",
                "--split=16", "--summary-interval=1", "--user-agent", ua,
                "--referer", url, "--check-certificate=false", direct_link
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            while True:
                line = await process.stdout.readline()
                if not line: break
                line_str = line.decode().strip()
                match = re.search(r'\((\d+)%\)', line_str)
                if match:
                    percentage = int(match.group(1))
                    size_match = re.search(r'(\d+(?:\.\d+)?\w+)/(\d+(?:\.\d+)?\w+)', line_str)
                    if size_match:
                        await progress_bar(percentage, 100, "📥 Aria2 ডাউনলোড হচ্ছে...", status_msg, last_update_time)
            await process.wait()

        # ২. বিকল্প ইঞ্জিন (YT-DLP) যদি Aria2 কাজ না করে বা প্রটেক্টেড সাইট হয়
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        
        if not files:
            await status_msg.edit_text("অ্যাডভান্সড ইঞ্জিন (YT-DLP) ব্যবহার হচ্ছে... 🔄")
            
            # প্রগ্রেস লজিক (হ্যাং এবং ইভেন্ট লুপ ফিক্সড)
            def ydl_progress_hook(d):
                if d['status'] == 'downloading':
                    current_bytes = d.get('downloaded_bytes', 0)
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                    
                    # মূল ইভেন্ট লুপে প্রগ্রেস বার পাঠানো (থ্রেড সেফ)
                    asyncio.run_coroutine_threadsafe(
                        progress_bar(current_bytes, total_bytes, "📥 অ্যাডভান্সড ডাউনলোড...", status_msg, last_update_time),
                        loop
                    )

            ydl_opts = {
                'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
                'progress_hooks': [ydl_progress_hook],
                'extractor_args': {'generic': ['impersonate']},
                'nocheckcertificate': True,
                'quiet': True,
                'no_warnings': True
            }
            
            # YT-DLP কে আলাদা থ্রেডে চালানো যাতে বট রেসপন্স করে
            await asyncio.to_thread(yt_dlp.YoutubeDL(ydl_opts).download, [url])
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]

        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ইনভ্যালিড অথবা প্রটেক্টেড।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # ইউজার ডেটা স্টোর (অরিজিনাল ফিচার)
        user_data[user_id] = {
            "file_path": file_path, "new_name": os.path.basename(file_path),
            "thumb": None, "dir": download_dir
        }

        await status_msg.delete()
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n"
            f"📄 **ফাইল:** `{os.path.basename(file_path)}` \n"
            f"💰 **সাইজ:** `{human_size(file_size)}` \n\n"
            "নাম বা থাম্বনেইল সেট করে আপলোড শুরু করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        logger.error(f"ডাউনলোড প্রসেস এরর: {e}")
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

# --- ৮. আপলোড সেকশন (Hybrid 4GB Support Logic - No Change) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data: return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    
    # এক্সটেনশন ফিক্সিং
    file_ext = os.path.splitext(old_path)[1]
    final_name = data["new_name"] if data["new_name"].endswith(file_ext) else data["new_name"] + file_ext
    
    new_path = os.path.join(os.path.dirname(old_path), final_name)
    os.rename(old_path, new_path)
    
    file_size = os.path.getsize(new_path)
    status_msg = await callback_query.message.edit_text("📤 আপলোড প্রস্তুতি চলছে...")
    video_dur = get_duration(new_path)
    last_update_time = [0]

    # আপলোড প্রগ্রেস কলব্যাক
    async def upload_progress(current, total):
        await progress_bar(current, total, "📤 ফাইল আপলোড হচ্ছে...", status_msg, last_update_time)

    try:
        # প্রিমিয়াম মোড ৪জিবি আপলোড (সেশন থাকলে)
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, video=new_path, duration=video_dur,
                thumb=data["thumb"], caption=f"✅ `{final_name}`",
                progress=upload_progress
            )
            # চ্যানেল থেকে ইউজারের কাছে কপি করা
            await app.copy_message(
                chat_id=user_id, from_chat_id=LOG_CHANNEL, message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{final_name}`\n💰 {human_size(file_size)}"
            )
        else:
            # ২জিবি সাধারণ মোড
            if file_size > 2000 * 1024 * 1024:
                return await status_msg.edit_text("❌ সেশন ছাড়া ২জিবির বড় ফাইল সম্ভব নয়।")
            await app.send_video(
                chat_id=user_id, video=new_path, duration=video_dur,
                thumb=data["thumb"], caption=f"✅ `{final_name}`",
                progress=upload_progress
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"আপলোড এরর: {e}")
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        # ক্লিনআপ
        if os.path.exists(data["dir"]): shutil.rmtree(data["dir"])
        if user_id in user_data: del user_data[user_id]

# ==============================================================================
# --- ৯. সিস্টেম রানার সেকশন (The Runner) ---
# ==============================================================================

async def start_services():
    """বট এবং ইউজার সেশন একসাথে স্টার্ট করার জন্য ফাইনাল মেথড।"""
    print("-" * 40)
    print("সার্ভার সিস্টেম চালু হচ্ছে... (Version 10.0)")
    
    await app.start()
    print("মূল বট ক্লায়েন্ট স্টার্ট হয়েছে! ✅")
    
    if user_app:
        try:
            await user_app.start()
            print("প্রিমিয়াম ইউজার ক্লায়েন্ট স্টার্ট হয়েছে! ✅")
        except Exception as e:
            print(f"সেশন ফেইল: {e}")
    
    print("বট এখন পুরোপুরি অনলাইন এবং ১০০% রেসপন্স করার জন্য প্রস্তুত! 🚀")
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
