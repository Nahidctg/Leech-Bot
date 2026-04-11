# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 18.0 - Full Original Master) ---
# --- ফিচার: স্মার্ট ডিকোড ইঞ্জিন, ৪জিবি হাইব্রিড সাপোর্ট, ফ্লাড প্রোটেকশন (৫ সেকেন্ড) ---
# --- বিশেষ আপডেট: ডাউনলোড ও আপলোড উভয় ক্ষেত্রেই ১০০% বক্স প্রগ্রেস বার (Speed + ETA) ---
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
# এটি বটের ইন্টারনাল মুভমেন্ট ট্র্যাকিং এর জন্য জরুরি।
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন (Detailed Config - No Changes Allowed) ---
# ==============================================================================

# আপনার টেলিগ্রাম এপিআই এবং বট ক্রেডেনশিয়ালস
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# --- ৪জিবি সাপোর্টের জন্য প্রিমিয়াম সেশন কনফিগারেশন ---
# আপনার সেশন স্ট্রিং থাকলে সেটি এখানে দিন। না থাকলে শুধু "" থাকবে।
STRING_SESSION = "" 
# লগ চ্যানেল আইডি যেখানে ৪জিবি ফাইলগুলো প্রথমে যাবে
LOG_CHANNEL = -1002491365982 

# মেইন বট ক্লায়েন্ট ইনিশিয়ালাইজেশন
app = Client(
    "ultimate_bot_instance", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    workers=100
)

# প্রিমিয়াম ইউজার অ্যাপ ক্লায়েন্ট
user_app = None
if STRING_SESSION and len(STRING_SESSION) > 10:
    user_app = Client(
        "premium_session_account", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

# ইউজারের ডাউনলোড ডেটা, সেটিংস এবং টেম্পোরারি স্টেট স্টোর
user_data = {}

# ==============================================================================
# --- ২. কোর ইউটিলিটি ফাংশনসমূহ (Full Detailed Helpers) ---
# ==============================================================================

def human_size(num):
    """বাইটকে মানুষের পাঠযোগ্য রিডেবল ফরম্যাটে রূপান্তর করে (KB, MB, GB, TB)"""
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
    """হাচোয়ার লাইব্রেরি ব্যবহার করে ভিডিওর সঠিক সময়কাল (Duration) বের করে।"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception as e:
        logger.error(f"ডিউরেশন এক্সট্রাকশন এরর: {e}")
    return 0

# ==============================================================================
# --- ৩. ইউনিফাইড প্রিমিয়াম প্রগ্রেস বার (বক্স ডিজাইন UI - ১০০% গ্যারান্টি) ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, start_time, last_update_time):
    """
    টেলিগ্রামের ফ্লাড প্রোটেকশন মাথায় রেখে ৫ সেকেন্ড পর পর সুন্দর বক্স ডিজাইনে প্রগ্রেস আপডেট করে।
    এটি ডাউনলোড এবং আপলোড—উভয় হ্যান্ডলারের সাথেই কানেক্টেড।
    """
    now = time.time()
    # ৫ সেকেন্ডের ব্যবধান বজায় রাখা হচ্ছে (ফ্লাড প্রোটেকশন)
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    # স্পিড এবং পার্সেন্টেজ ক্যালকুলেশন
    elapsed_time = now - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    percentage = (current * 100) / total if total > 0 else 0
    
    # ইটিএ (বাকি সময়) ক্যালকুলেশন
    remaining_bytes = total - current
    eta = remaining_bytes / speed if speed > 0 else 0
    
    # আপনার পছন্দের প্রিমিয়াম বক্স ডিজাইন প্রগ্রেস বার
    bar_length = 12
    filled_length = int(percentage / (100 / bar_length))
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
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
        # মেসেজটি এডিট করে লাইভ আপডেট পাঠানো
        await status_msg.edit_text(progress_ui)
    except errors.FloodWait as f:
        # টেলিগ্রাম থেকে ফ্লাড ওয়েট আসলে অটোমেটিক ওয়েট করবে
        await asyncio.sleep(f.value)
    except Exception as e:
        logger.error(f"UI আপডেট এরর: {e}")

# ==============================================================================
# --- ৪. স্মার্ট লিঙ্ক রেজলভার ENGINE (Ultra Decoder + Speed Bypass) ---
# ==============================================================================

def get_smart_link(url):
    """
    এটি স্মার্টলি লিঙ্ক রিডাইরেক্ট এনালাইসিস করে এবং সঠিক স্ট্রিমিং লিঙ্ক বের করে।
    Kraken, Vidara এবং সরাসরি লিঙ্কগুলো এখানে ডিকোড হয়।
    """
    print(f"DEBUG: এনালাইসিস শুরু হচ্ছে - {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': url
    }

    # ১. সরাসরি ভিডিও ফাইল কিনা চেক করা
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, allow_redirects=True, timeout=15, stream=True)
        final_url = response.url
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.ts']):
            return final_url
        url = final_url
    except Exception as e:
        print(f"লিঙ্ক ডিকোড ইঞ্জিন এরর: {e}")

    # ২. YT-DLP স্ক্যান ফর প্রিমিয়াম সাইটস
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
        except Exception:
            return url

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ (The Main Core System) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    """বট স্টার্ট কমান্ড যা ইউজারের সামনে ইন্টারফেস ওপেন করে।"""
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    
    welcome_text = (
        f"**বট অনলাইন! 🚀 (Version 18.0 - Master Final)**\n\n"
        f"এখন Kraken, Vidara সহ যেকোনো লিঙ্ক সুপার-ফাস্ট গতিতে ডাউনলোড হবে।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n"
        f"**প্রগ্রেস ইন্টারভাল:** `৫ সেকেন্ড`\n\n"
        f"যেকোনো ভিডিও লিঙ্ক পাঠান। ডাউনলোড এবং আপলোড উভয় ক্ষেত্রে বক্স ডিজাইন দেখতে পাবেন।"
    )
    await message.reply_text(welcome_text)

# ==============================================================================
# --- ৬. ডাউনলোড সেকশন (Speed Booster + Working Progress Hook) ---
# ==============================================================================

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """ভিডিও ডাউনলোড এবং প্রগ্রেস বার প্রদর্শনের মেইন লজিক।"""
    url = message.text.strip()
    user_id = message.from_user.id
    loop = asyncio.get_event_loop()
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # ডাইরেক্ট লিঙ্ক এবং ডিকোডিং
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("ডাউনলোড ইঞ্জিন কনফিগার করা হচ্ছে... 📥")
    
    # ডাউনলোডের জন্য টেম্পোরারি ফোল্ডার তৈরি
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    start_time = time.time()
    last_update_time = [0] # ৫ সেকেন্ড লিমিট ট্র্যাক করার জন্য

    try:
        # প্রগ্রেস বার কল করার জন্য yt-dlp হুক
        def ydl_progress_hook(d):
            if d['status'] == 'downloading':
                current = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                # থ্রেড সেফ উপায়ে বক্স প্রগ্রেস বার কল করা
                asyncio.run_coroutine_threadsafe(
                    progress_bar(current, total, "ডাউনলোড হচ্ছে...", status_msg, start_time, last_update_time),
                    loop
                )

        # YT-DLP কনফিগারেশন (Aria2 এর বদলে এখানে মাল্টি-থ্রেড ব্যবহার করা হয়েছে প্রগ্রেস বারের জন্য)
        ydl_opts = {
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'progress_hooks': [ydl_progress_hook],
            'nocheckcertificate': True, 
            'quiet': True,
            'no_warnings': True,
            'format': 'bestvideo+bestaudio/best',
            'concurrent_fragment_downloads': 10, # স্পিড বুস্টার (১০ থ্রেড)
            'buffersize': 1024 * 64
        }
        
        # ব্লকিং ফাংশনটি থ্রেডে রান করা
        await asyncio.to_thread(yt_dlp.YoutubeDL(ydl_opts).download, [url])
        
        # ডাউনলোড করা ফাইলটি সিলেক্ট করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ইনভ্যালিড অথবা প্রটেক্টেড।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # ইউজার ডেটা স্টোর (রিনেম ও থাম্বনেইলের জন্য)
        user_data[user_id] = {
            "file_path": file_path, 
            "new_name": os.path.basename(file_path),
            "thumb": None, 
            "dir": download_dir
        }

        await status_msg.delete()
        
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n"
            f"📄 **ফাইল:** `{os.path.basename(file_path)}` \n"
            f"💰 **সাইজ:** `{human_size(file_size)}` \n\n"
            f"নাম বা থাম্বনেইল পাঠিয়ে ফাইলটি কাস্টমাইজ করতে পারেন অথবা আপলোড দিন।",
            reply_markup=markup
        )

    except Exception as e:
        logger.error(f"ডাউনলোড এরর: {e}")
        await status_msg.edit_text(f"❌ ডাউনলোড এরর: {str(e)}")

# ==============================================================================
# --- ৭. রিনেম ও থাম্বনেইল হ্যান্ডলার (Full Logic) ---
# ==============================================================================

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    """ইউজার টেক্সট দিলে রিনেম এবং ফটো দিলে থাম্বনেইল হিসেবে সেট হবে।"""
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন নাম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট করা হয়েছে!")

# ==============================================================================
# --- ৮. আপলোড সেকশন (Hybrid 4GB Logic + Box UI Progress) ---
# ==============================================================================

@app.on_callback_query(filters.regex("upload"))
async def upload_callback_handler(client, callback_query):
    """আপলোড বাটনে ক্লিক করলে ফাইলটি টেলিগ্রামে পাঠিয়ে দিবে।"""
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ডেটা পাওয়া যায়নি! নতুন করে লিঙ্ক পাঠান।", show_alert=True)
        return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    
    # নতুন নাম অনুযায়ী ফাইল রিনেম করা
    ext = os.path.splitext(old_path)[1]
    final_name = data["new_name"] if data["new_name"].endswith(ext) else data["new_name"] + ext
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

        # ৪জিবি হাইব্রিড লজিক (সেশন চেক)
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, 
                video=new_path, 
                duration=duration,
                thumb=data["thumb"], 
                caption=f"✅ `{final_name}`", 
                progress=upload_progress
            )
            
            # চ্যানেল থেকে ইউজারের ইনবক্সে কপি পাঠানো
            await app.copy_message(
                chat_id=user_id, 
                from_chat_id=LOG_CHANNEL, 
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{final_name}`\n💰 **সাইজ:** `{human_size(file_size)}`"
            )
        else:
            # ২জিবি লিমিট চেক
            if file_size > 2000*1024*1024:
                await status_msg.edit_text("❌ ২জিবির বড় ফাইল। সেশন ছাড়া আপলোড সম্ভব নয়।")
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
        # টেম্পোরারি ফোল্ডার পরিষ্কার করা
        if os.path.exists(data["dir"]):
            shutil.rmtree(data["dir"], ignore_errors=True)
        if user_id in user_data:
            del user_data[user_id]

# ==============================================================================
# --- ৯. সিস্টেম রানার সেকশন (The Final Detailed Runner) ---
# ==============================================================================

async def start_all_services():
    """বট এবং ইউজার ক্লায়েন্টকে লাইভ করার মাস্টার ফাংশন।"""
    print("-" * 50)
    print("আলটিমেট টেলিগ্রাম ইঞ্জিন স্টার্ট হচ্ছে... (Version 18.0)")
    
    # মূল বট স্টার্ট
    await app.start()
    bot_info = await app.get_me()
    print(f"বট ক্লায়েন্ট স্টার্ট হয়েছে: @{bot_info.username} ✅")
    
    # সেশন থাকলে প্রিমিয়াম অ্যাপ স্টার্ট
    if user_app:
        try:
            await user_app.start()
            premium_info = await user_app.get_me()
            print(f"প্রিমিয়াম ইউজার সেশন অনলাইন: {premium_info.first_name} ✅")
        except Exception as e:
            print(f"⚠️ প্রিমিয়াম সেশন এরর: {e}")
    
    print("সার্ভার এখন পুরোপুরি অনলাইন! 🚀")
    print("-" * 50)
    
    await idle() # বটকে সচল রাখা
    
    # শাটডাউন
    await app.stop()
    if user_app:
        await user_app.stop()

if __name__ == "__main__":
    try:
        # মেইন লুপ রান করা
        asyncio.get_event_loop().run_until_complete(start_all_services())
    except KeyboardInterrupt:
        print("\nবট শাটডাউন করা হয়েছে।")
