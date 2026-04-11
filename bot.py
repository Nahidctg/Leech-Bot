# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 16.0 - The Full Master) ---
# --- ফিচার: স্মার্ট ডিকোড ইঞ্জিন, ৪জিবি হাইব্রিড সাপোর্ট, ফ্লাড প্রোটেকশন (৫ সেকেন্ড) ---
# --- বিশেষ আপডেট: ডাউনলোড ও আপলোড উভয় ক্ষেত্রেই প্রিমিয়াম বক্স প্রগ্রেস বার (Speed + ETA) ---
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
from datetime import datetime
from urllib.parse import urlparse
from pyrogram import Client, filters, idle, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# লগার সেটআপ (বিস্তারিত লগ দেখার জন্য যা ডিবাগিং এ সাহায্য করবে)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন (Detailed Config Structure) ---
# ==============================================================================

# আপনার টেলিগ্রাম এপিআই ক্রেডেনশিয়ালস
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# ৪জিবি সাপোর্টের জন্য প্রিমিয়াম সেশন (না থাকলে বট ২জিবি মোডে চলবে)
# সেশন থাকলে অবশ্যই LOG_CHANNEL আইডি দিন।
STRING_SESSION = "" 
LOG_CHANNEL = -1002491365982 

# ক্লায়েন্ট ইনিশিয়ালাইজেশন (বট এবং প্রিমিয়াম সেশন)
app = Client(
    "ultimate_bot_instance", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    workers=100
)

user_app = None
if STRING_SESSION and len(STRING_SESSION) > 10:
    user_app = Client(
        "premium_session_account", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

# ইউজারের ডাউনলোড ডেটা এবং সেটিংস স্টোর করার ডিকশনারি
user_data = {}

# ==============================================================================
# --- ২. কোর ইউটিলিটি ফাংশনসমূহ (Full Detailed Helpers) ---
# ==============================================================================

def human_size(num):
    """বাইটকে মানুষের পাঠযোগ্য ফরম্যাটে (KB, MB, GB) রূপান্তর করে।"""
    if not num:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

def time_formatter(seconds):
    """সেকেন্ডকে সুন্দর সময় ফরম্যাটে (ঘণ্টা, মিনিট, সেকেন্ড) রূপান্তর করে।"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def get_duration(file_path):
    """হাচোয়ার লাইব্রেরি ব্যবহার করে ভিডিও ফাইলের সঠিক ডিউরেশন বের করে।"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception as e:
        logger.error(f"ডিউরেশন এক্সট্রাকশন এরর: {e}")
    return 0

# ==============================================================================
# --- ৩. ইউনিফাইড প্রিমিয়াম প্রগ্রেস বার (ডাউনলোড ও আপলোড উভয়ের জন্য বক্স UI) ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, start_time, last_update_time):
    """
    টেলিগ্রামের ফ্লাড প্রোটেকশন মাথায় রেখে ৫ সেকেন্ড পর পর সুন্দর বক্স ডিজাইনে প্রগ্রেস আপডেট করে।
    এতে ডাউনলোড/আপলোড স্পিড এবং ইটিএ (ETA) লাইভ দেখা যায়।
    """
    now = time.time()
    # ৫ সেকেন্ডের ব্যবধান চেক করা হচ্ছে
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    # স্পিড এবং শতাংশ ক্যালকুলেশন
    elapsed_time = now - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    percentage = (current * 100) / total if total > 0 else 0
    
    # ইটিএ (বাকি সময়) ক্যালকুলেশন
    remaining_bytes = total - current
    eta = remaining_bytes / speed if speed > 0 else 0
    
    # বক্স ডিজাইন প্রগ্রেস বার (User Requested Style)
    bar_length = 12
    filled_length = int(percentage / (100 / bar_length))
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    # প্রিমিয়াম ভিজ্যুয়াল লেআউট
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
        # মেসেজ এডিট করে ইউজারকে আপডেট দেওয়া
        await status_msg.edit_text(progress_ui)
    except errors.FloodWait as f:
        await asyncio.sleep(f.value)
    except Exception as e:
        logger.error(f"প্রগ্রেস বার এডিট এরর: {e}")

# ==============================================================================
# --- ৪. স্মার্ট লিঙ্ক রেজলভার ENGINE (Ultra Decoder + Speed Bypass) ---
# ==============================================================================

def get_smart_link(url):
    """
    এটি রিডাইরেক্ট চেক করে, সরাসরি ফাইল লিঙ্ক খুঁজে বের করে এবং 
    YT-DLP এর মাধ্যমে জটিল লিঙ্কের সমাধান করে।
    """
    print(f"DEBUG: লিঙ্ক এনালাইসিস শুরু হচ্ছে - {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': url
    }

    # ১. প্রথম ধাপে সরাসরি রিডাইরেক্ট চেক
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, allow_redirects=True, timeout=15, stream=True)
        final_url = response.url
        # যদি লিঙ্কে সরাসরি ভিডিও এক্সটেনশন থাকে
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.ts']):
            return final_url
        url = final_url
    except Exception as e:
        print(f"লিঙ্ক রেজলভার এরর: {e}")

    # ২. দ্বিতীয় ধাপে YT-DLP স্ক্যান (Kraken, Terabox ইত্যাদি হ্যান্ডেল করার জন্য)
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'format': 'best',
        'noplaylist': True, 
        'nocheckcertificate': True,
        'extractor_args': {'generic': ['impersonate']},
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('url', url)
        except Exception as e:
            print(f"YT-DLP রেজলভার এরর: {e}")
            return url

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ (The Main Core Logic) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    """বট স্টার্ট করার কমান্ড এবং বর্তমান মোড প্রদর্শন।"""
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    
    welcome_text = (
        f"**বট অনলাইন! 🚀 (Version 16.0 - Full Master)**\n\n"
        f"এখন Kraken, Vidara সহ যেকোনো লিঙ্ক সুপার-ফাস্ট গতিতে ডাউনলোড হবে।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n"
        f"**আপডেট ইন্টারভাল:** `৫ সেকেন্ড`\n\n"
        f"যেকোনো ভিডিও লিঙ্ক পাঠান। ডাউনলোড এবং আপলোড উভয় ক্ষেত্রে প্রিমিয়াম বক্স ডিজাইন দেখতে পাবেন।"
    )
    await message.reply_text(welcome_text)

# ==============================================================================
# --- ৬. ডাউনলোড সেকশন (Aria2 Multi-thread Speed Booster) ---
# ==============================================================================

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """লিঙ্ক রিসিভ করা এবং প্রসেস করার মূল ফাংশন।"""
    url = message.text.strip()
    user_id = message.from_user.id
    loop = asyncio.get_event_loop()
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # ডাইরেক্ট লিঙ্ক ডিকোড করা
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে সুপার-ফাস্ট ডাউনলোড শুরু হচ্ছে... 📥")
    
    # ডাউনলোডের জন্য ইউনিক ফোল্ডার তৈরি
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    start_time = time.time()
    last_update_time = [0] # লিস্ট ব্যবহার করা হয়েছে যাতে ফাংশনের ভেতর মডিফাই করা যায়

    try:
        # ডাউনলোড প্রসেসের প্রগ্রেস হুক
        def ydl_progress_hook(d):
            if d['status'] == 'downloading':
                current = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                # থ্রেড সেফ উপায়ে প্রগ্রেস বার কল করা
                asyncio.run_coroutine_threadsafe(
                    progress_bar(current, total, "ডাউনলোড হচ্ছে...", status_msg, start_time, last_update_time),
                    loop
                )

        # YT-DLP + Aria2 এক্সটার্নাল স্পিড বুস্টার কনফিগারেশন
        ydl_opts = {
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'progress_hooks': [ydl_progress_hook],
            'extractor_args': {'generic': ['impersonate']},
            'external_downloader': 'aria2c', 
            'external_downloader_args': [
                '--max-connection-per-server=16', 
                '--split=16', 
                '--min-split-size=1M',
                '--summary-interval=0'
            ],
            'nocheckcertificate': True, 
            'quiet': True,
            'no_warnings': True
        }
        
        # ব্লকিং ফাংশনটি থ্রেডে রান করা হচ্ছে যাতে বট রেসপন্স করে
        await asyncio.to_thread(yt_dlp.YoutubeDL(ydl_opts).download, [url])
        
        # ডাউনলোড করা ফাইলটি খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ইনভ্যালিড অথবা প্রটেক্টেড।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # ইউজার ডেটা স্টোর করা রিনেম এবং থাম্বনেইলের জন্য
        user_data[user_id] = {
            "file_path": file_path, 
            "new_name": os.path.basename(file_path),
            "thumb": None, 
            "dir": download_dir
        }

        await status_msg.delete()
        
        finish_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]
        ])
        
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n"
            f"📄 **ফাইল:** `{os.path.basename(file_path)}` \n"
            f"💰 **সাইজ:** `{human_size(file_size)}` \n\n"
            f"আপনি চাইলে এখন নতুন নাম বা থাম্বনেইল পাঠিয়ে ফাইলটি কাস্টমাইজ করতে পারেন। অন্যথায় আপলোড বাটনে ক্লিক করুন।",
            reply_markup=finish_markup
        )

    except Exception as e:
        logger.error(f"ডাউনলোড এরর: {e}")
        await status_msg.edit_text(f"❌ ডাউনলোড এরর: {str(e)}")

# ==============================================================================
# --- ৭. কাস্টমাইজেশন হ্যান্ডলার (Rename & Thumbnail) ---
# ==============================================================================

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    """ইউজার টেক্সট পাঠালে নাম পরিবর্তন এবং ফটো পাঠালে থাম্বনেইল সেট করবে।"""
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if message.text:
        # নতুন ফাইল নাম সেট করা
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন ফাইল নেম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        # থাম্বনেইল ডাউনলোড করে স্টোর করা
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট করা হয়েছে!")

# ==============================================================================
# --- ৮. আপলোড সেকশন (Hybrid 4GB Support + Box UI Progress) ---
# ==============================================================================

@app.on_callback_query(filters.regex("upload"))
async def upload_callback_handler(client, callback_query):
    """আপলোড বাটনে ক্লিক করলে ফাইলটি টেলিগ্রামে আপলোড করবে।"""
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ডেটা পাওয়া যায়নি! আবার ট্রাই করুন।", show_alert=True)
        return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    
    # ফাইল নেম প্রিপারেশন
    ext = os.path.splitext(old_path)[1]
    final_name = data["new_name"]
    if not final_name.endswith(ext):
        final_name += ext
        
    new_path = os.path.join(os.path.dirname(old_path), final_name)
    os.rename(old_path, new_path)
    
    status_msg = await callback_query.message.edit_text("📤 আপলোড প্রস্তুতি চলছে...")
    start_time = time.time()
    last_update_time = [0]

    # আপলোড প্রগ্রেস কলব্যাক
    async def upload_progress(current, total):
        await progress_bar(current, total, "আপলোড হচ্ছে...", status_msg, start_time, last_update_time)

    try:
        file_size = os.path.getsize(new_path)
        duration = get_duration(new_path)

        # ৪জিবি হাইব্রিড আপলোড লজিক
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে ব্যবহার করে আপলোড হচ্ছে...")
            
            # প্রিমিয়াম একাউন্ট দিয়ে লগ চ্যানেলে আপলোড
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, 
                video=new_path, 
                duration=duration,
                thumb=data["thumb"], 
                caption=f"✅ `{final_name}`", 
                progress=upload_progress
            )
            
            # চ্যানেল থেকে ইউজারের ইনবক্সে কপি (Original Logic)
            await app.copy_message(
                chat_id=user_id, 
                from_chat_id=LOG_CHANNEL, 
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{final_name}`\n💰 **সাইজ:** `{human_size(file_size)}`"
            )
        else:
            # নরমাল ২জিবি আপলোড লিমিট চেক
            if file_size > 2000*1024*1024:
                await status_msg.edit_text("❌ ফাইলটি ২জিবির বড়। প্রিমিয়াম সেশন ছাড়া এটি আপলোড সম্ভব নয়।")
                return
                
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
        logger.error(f"আপলোড এরর: {e}")
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
        
    finally:
        # কাজ শেষে টেম্পোরারি ফাইল এবং ফোল্ডার ক্লিন করা
        if os.path.exists(data["dir"]):
            shutil.rmtree(data["dir"], ignore_errors=True)
        if user_id in user_data:
            del user_data[user_id]

# ==============================================================================
# --- ৯. সিস্টেম রানার সেকশন (The Final Engine Runner) ---
# ==============================================================================

async def start_all_services():
    """বট এবং ইউজার ক্লায়েন্ট একসাথে চালু করার ফাংশন।"""
    print("-" * 50)
    print("সার্ভার সিস্টেম স্টার্ট হচ্ছে... (Version 16.0)")
    
    # মেইন বট স্টার্ট
    await app.start()
    bot_info = await app.get_me()
    print(f"বট ক্লায়েন্ট স্টার্ট হয়েছে: @{bot_info.username} ✅")
    
    # সেশন থাকলে প্রিমিয়াম অ্যাপ স্টার্ট
    if user_app:
        try:
            await user_app.start()
            premium_info = await user_app.get_me()
            print(f"প্রিমিয়াম ইউজার স্টার্ট হয়েছে: {premium_info.first_name} ✅")
        except Exception as e:
            print(f"⚠️ প্রিমিয়াম সেশন স্টার্ট করতে সমস্যা হয়েছে: {e}")
    
    print("বট এখন পুরোপুরি অনলাইন এবং রেসপন্স করার জন্য প্রস্তুত! 🚀")
    print("-" * 50)
    
    await idle() # বটকে রানিং রাখা
    
    # শাটডাউন প্রসেস
    await app.stop()
    if user_app:
        await user_app.stop()

if __name__ == "__main__":
    try:
        # ইভেন্ট লুপ রান করা
        asyncio.get_event_loop().run_until_complete(start_all_services())
    except KeyboardInterrupt:
        print("\nবট বন্ধ করা হয়েছে।")
