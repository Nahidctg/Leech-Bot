# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 5.0 - Final Fix) ---
# --- ফিচার: স্মার্ট ডিকোড ইঞ্জিন, ৪জিবি হাইব্রিড সাপোর্ট, ফ্লাড প্রোটেকশন ---
# ==============================================================================

import os
import time
import asyncio
import subprocess
import shutil
import re
import requests
import yt_dlp
from urllib.parse import urlparse
from pyrogram import Client, filters, idle, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন (Config) ---
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
# --- ২. কোর ইউটিলিটি ফাংশনসমূহ (Helpers) ---
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
        print(f"ডিউরেশন এরর: {e}")
    return 0

# ==============================================================================
# --- ৩. স্মার্ট লিঙ্ক রেজলভার ENGINE (Smart AI Decoder) ---
# ==============================================================================

def get_smart_link(url):
    """
    এটি একটি পাওয়ারফুল সিনক্রোনাস ফাংশন যা রিডাইরেক্ট এবং স্মার্ট লিঙ্ক ফিক্স করে।
    এটি asyncio.to_thread এর মাধ্যমে কল হবে যাতে বট হ্যাং না হয়।
    """
    print(f"সার্চিং অরিজিনাল লিঙ্ক: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': url
    }

    # ১. রিডাইরেক্ট এবং মুভি সাইট গেটওয়ে বাইপাস
    try:
        session = requests.Session()
        session.headers.update(headers)
        # ৫ সেকেন্ডের মধ্যে রিডাইরেক্ট ফলো করে আসল গন্তব্য বের করবে
        response = session.get(url, allow_redirects=True, timeout=10, stream=True)
        final_url = response.url
        
        # যদি সরাসরি ডাউনলোডযোগ্য ফাইল পাওয়া যায়
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.mp3']):
            print(f"সরাসরি লিঙ্ক পাওয়া গেছে: {final_url}")
            return final_url
        url = final_url
    except Exception as e:
        print(f"Redirect Analysis Error: {e}")

    # ২. YT-DLP ব্যবহার করে ডিপ স্ক্যান (মুভি সাইট এবং ড্রাইভ ক্লাউড এর জন্য)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'noplaylist': True,
        'user_agent': headers['User-Agent'],
        'nocheckcertificate': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            smart_url = info.get('url', url)
            print(f"Engine লিঙ্ক খুঁজে পেয়েছে: {smart_url}")
            return smart_url
        except Exception as e:
            print(f"Engine Error: {e}. অরিজিনাল লিঙ্কই ব্যবহার হচ্ছে।")
            return url

# ==============================================================================
# --- ৪. অরিজিনাল প্রগ্রেস বার ফাংশন (বিস্তারিত লজিক) ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    """ডাউনলোড এবং আপলোড চলাকালীন আপনার অরিজিনাল স্টাইলের বিস্তারিত বার।"""
    now = time.time()
    if (now - last_update_time[0]) < 5:
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
    except Exception:
        pass

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ (The Core System) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    """বট স্টার্ট হ্যান্ডলার (রেসপন্স চেক প্রিন্ট সহ)"""
    print(f"DEBUG: Start কমান্ড দিয়েছেন: {message.from_user.id}")
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    
    await message.reply_text(
        f"**বট অনলাইন এবং ১০০% রেসপন্স করার জন্য প্রস্তুত! 🚀**\n\n"
        f"এখন যেকোনো লিঙ্ক পাঠান, আমি সেটি অটো-বাইপাস করে দেব।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n\n"
        f"যেকোনো মুভি বা ভিডিও লিঙ্ক পাঠান।"
    )

# --- ৬. ডাউনলোড সেকশন (Aria2 Engine + Smart Decoder) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """লিঙ্ক পাওয়ার পর অটো-বাইপাস এবং ডাউনলোড প্রসেস।"""
    url = message.text.strip()
    user_id = message.from_user.id
    print(f"নতুন লিঙ্ক এসেছে: {url}")
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # --- ফিক্স: get_smart_link এখন সঠিকভাবে থ্রেডে কল হবে (Await Error Fix) ---
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে হাই-স্পিড ডাউনলোড শুরু হচ্ছে... 📥")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        # Aria2 কমান্ড সেটআপ
        cmd = [
            "aria2c", "--dir", download_dir, "--max-connection-per-server=16",
            "--split=16", "--summary-interval=1", "--user-agent", ua,
            "--referer", url, "--check-certificate=false", direct_link
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        last_update_time = [0]
        
        while True:
            line = await process.stdout.readline()
            if not line: break
            
            line_str = line.decode().strip()
            
            # প্রগ্রেস এবং সাইজ রিড করার জন্য আপনার অরিজিনাল Regex
            match = re.search(r'\((\d+)%\)', line_str)
            if match:
                percentage = int(match.group(1))
                size_match = re.search(r'(\d+(?:\.\d+)?\w+)/(\d+(?:\.\d+)?\w+)', line_str)
                
                if size_match:
                    curr_sz = size_match.group(1)
                    total_sz = size_match.group(2)
                    
                    if (time.time() - last_update_time[0]) > 5:
                        last_update_time[0] = time.time()
                        try:
                            await status_msg.edit_text(
                                f"**📥 সার্ভারে ডাউনলোড হচ্ছে...**\n\n"
                                f"🌀 প্রগ্রেস: **{percentage}%**\n"
                                f"📦 সাইজ: `{curr_sz}` / `{total_sz}`"
                            )
                        except: pass

        await process.wait()

        # ডাউনলোড হওয়া ফাইলটি খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ফিক্সড নয় অথবা সার্ভার রেসপন্স দিচ্ছে না।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

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
        await status_msg.edit_text(f"❌ এরর: {str(e)}")

# --- ৭. রিনেম ও থাম্বনেইল হ্যান্ডলার (Customization) ---

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

# --- ৮. আপলোড সেকশন (The Hybrid Support Logic) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data: return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    new_path = os.path.join(os.path.dirname(old_path), data["new_name"])
    os.rename(old_path, new_path)
    
    file_size = os.path.getsize(new_path)
    status_msg = await callback_query.message.edit_text("📤 আপলোড প্রস্তুতি চলছে...")
    video_dur = get_duration(new_path)
    last_update_time = [0]

    try:
        # প্রিমিয়াম মোড ৪জিবি আপলোড
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, video=new_path, duration=video_dur,
                thumb=data["thumb"], caption=f"✅ `{data['new_name']}`",
                progress=progress_bar, progress_args=("📤 প্রিমিয়াম আপলোড...", status_msg, last_update_time)
            )
            await app.copy_message(chat_id=user_id, from_chat_id=LOG_CHANNEL, message_id=sent_msg.id,
                                   caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 {human_size(file_size)}")
        else:
            # ২জিবি সাধারণ মোড
            if file_size > 2000 * 1024 * 1024:
                return await status_msg.edit_text("❌ ২জিবির বড় ফাইল। সেশন প্রয়োজন।")
            await app.send_video(
                chat_id=user_id, video=new_path, duration=video_dur,
                thumb=data["thumb"], caption=f"✅ `{data['new_name']}`",
                progress=progress_bar, progress_args=("📤 সরাসরি আপলোড...", status_msg, last_update_time)
            )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        if os.path.exists(data["dir"]): shutil.rmtree(data["dir"])
        if user_id in user_data: del user_data[user_id]

# ==============================================================================
# --- ৯. সিস্টেম এক্সিকিউশন সেকশন (The Runner) ---
# ==============================================================================

async def start_services():
    """বট এবং ইউজার সেশন একসাথে স্টার্ট করার জন্য ফাইনাল ফিক্সড মেথড।"""
    print("-" * 40)
    print("সার্ভার সিস্টেম চালু হচ্ছে...")
    
    # মূল বট স্টার্ট করা
    await app.start()
    print("মূল বট ক্লায়েন্ট স্টার্ট হয়েছে! ✅")
    
    # সেশন স্টার্ট করা
    if user_app:
        try:
            await user_app.start()
            print("প্রিমিয়াম ইউজার ক্লায়েন্ট স্টার্ট হয়েছে! (4GB Enabled) ✅")
        except Exception as e:
            print(f"সেশন ফেইল: {e}")
    
    print("বট এখন পুরোপুরি অনলাইন এবং রেসপন্স করার জন্য প্রস্তুত! 🚀")
    print("-" * 40)
    
    # নিশ্চিত করা যাতে কমান্ডে রেসপন্স করে
    await idle()
    
    # বন্ধ করার সময়
    await app.stop()
    if user_app: await user_app.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        print("বট বন্ধ করা হয়েছে।")
