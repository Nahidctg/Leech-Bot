# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 5.1 - Site Bypass Update) ---
# --- ফিচার: Kraken, Flash-Files, Vidara & Fredl সাপোর্ট সহ ---
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
# --- ১. গলোবাল কনফিগারেশন সেকশন (Config) ---
# ==============================================================================

API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

STRING_SESSION = "" 
LOG_CHANNEL = -1002491365982 

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

user_data = {}

# ==============================================================================
# --- ২. কোর ইউটিলিটি ফাংশনসমূহ (Helpers) ---
# ==============================================================================

def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

def get_duration(file_path):
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception:
        pass
    return 0

# ==============================================================================
# --- ৩. স্মার্ট লিঙ্ক রেজলভার ENGINE (Special Scraper Added) ---
# ==============================================================================

def get_smart_link(url):
    print(f"সার্চিং অরিজিনাল লিঙ্ক: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': url
    }

    # --- বিশেষ সাইট হ্যান্ডলিং (Krakenfiles) ---
    if "krakenfiles.com" in url:
        try:
            response = requests.get(url, headers=headers)
            # স্ক্র্যাপ করে ডাউনলোড টোকেন বের করা
            match = re.search(r'token: "([^"]+)"', response.text)
            if match:
                token = match.group(1)
                # ক্রাকেনফাইলস এর ডাউনলোড URL জেনারেট করা (এটি অনেক সময় কাজে দেয়)
                post_url = f"https://krakenfiles.com/download/{url.split('/')[-1]}"
                return url # yt-dlp ক্রাকেন ভালো হ্যান্ডেল করে, তাই অরিজিনালই রাখা হলো
        except: pass

    # --- ১. রিডাইরেক্ট এবং সরাসরি ফাইল চেক ---
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, allow_redirects=True, timeout=15, stream=True)
        final_url = response.url
        
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.mp3']):
            return final_url
        url = final_url
    except Exception as e:
        print(f"Redirect Error: {e}")

    # --- ২. YT-DLP অ্যাডভান্সড স্ক্যান (Vidara, Fredl, Kraken এর জন্য) ---
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'user_agent': headers['User-Agent'],
        'nocheckcertificate': True,
        'cookiefile': None # প্রয়োজনে কুকি ফাইল এড করা যায়
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            # ড্রাইভ বা অন্যান্য ডিরেক্ট লিঙ্ক খুঁজে পেলে তা রিটার্ন করবে
            smart_url = info.get('url', url)
            return smart_url
        except Exception as e:
            print(f"YT-DLP Engine Error: {e}")
            return url

# ==============================================================================
# --- ৪. প্রগ্রেস বার ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    now = time.time()
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    percentage = (current * 100) / total if total > 0 else 0
    bar_length = 10
    filled_length = int(percentage // 10)
    bar = "▰" * filled_length + "▱" * (bar_length - filled_length)
    
    try:
        await status_msg.edit_text(
            f"**{status_text}**\n\n"
            f"🌀 {bar} **{round(percentage, 2)}%**\n"
            f"📦 সাইজ: `{human_size(current)}` / `{human_size(total)}`"
        )
    except: pass

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    await message.reply_text(
        f"**বট অনলাইন! Kraken, Vidara, Flash-Files সাপোর্ট যুক্ত করা হয়েছে। 🚀**\n\n"
        f"**বর্তমান মোড:** `{mode}`\n\n"
        f"লিঙ্ক পাঠান, আমি প্রসেস করছি।"
    )

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি বাইপাস করছে... 🔎")
    
    # বাইপাস ইঞ্জিন কল
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে হাই-স্পিড ডাউনলোড শুরু হচ্ছে... 📥")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    try:
        # Aria2 কমান্ড (Referer এবং UA খুব গুরুত্বপূর্ণ এই সাইটগুলোর জন্য)
        cmd = [
            "aria2c", 
            "--dir", download_dir, 
            "--max-connection-per-server=16",
            "--split=16", 
            "--summary-interval=1", 
            "--user-agent", ua,
            "--referer", url, # অরিজিনাল লিঙ্ককে রেফারার হিসেবে রাখা হয়েছে
            "--check-certificate=false", 
            "--max-tries=5",
            "--retry-wait=3",
            direct_link
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        last_update_time = [0]
        
        while True:
            line = await process.stdout.readline()
            if not line: break
            
            line_str = line.decode().strip()
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

        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            # যদি Aria2 ফেল করে, তবে yt-dlp দিয়ে সরাসরি ডাউনলোডের শেষ চেষ্টা করা
            await status_msg.edit_text("Aria2 ব্যর্থ হয়েছে। yt-dlp দিয়ে ট্রাই করছি... 🔄")
            ydl_cmd = f'yt-dlp -o "{download_dir}/%(title)s.%(ext)s" "{url}"'
            os.system(ydl_cmd)
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]

        if not files:
            await status_msg.edit_text("❌ দুঃখিত! এই লিঙ্কটি বাইপাস করা সম্ভব হচ্ছে না।")
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
            "এখন নাম বা থাম্বনেইল পরিবর্তন করতে পারেন অথবা সরাসরি আপলোড দিন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ এরর: {str(e)}")

# --- ৭. রিনেম ও থাম্বনেইল (অপরিবর্তিত) ---

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

# --- ৮. আপলোড সেকশন (হাইব্রিড সাপোর্ট সহ) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data: return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    ext = os.path.splitext(old_path)[1]
    new_name = data["new_name"] if data["new_name"].endswith(ext) else data["new_name"] + ext
    new_path = os.path.join(os.path.dirname(old_path), new_name)
    os.rename(old_path, new_path)
    
    file_size = os.path.getsize(new_path)
    status_msg = await callback_query.message.edit_text("📤 আপলোড প্রস্তুতি চলছে...")
    video_dur = get_duration(new_path)
    last_update_time = [0]

    try:
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, video=new_path, duration=video_dur,
                thumb=data["thumb"], caption=f"✅ `{new_name}`",
                progress=progress_bar, progress_args=("📤 প্রিমিয়াম আপলোড...", status_msg, last_update_time)
            )
            await app.copy_message(chat_id=user_id, from_chat_id=LOG_CHANNEL, message_id=sent_msg.id,
                                   caption=f"✅ **ফাইল:** `{new_name}`\n💰 {human_size(file_size)}")
        else:
            if file_size > 2000 * 1024 * 1024:
                return await status_msg.edit_text("❌ ২জিবির বড় ফাইল। সেশন প্রয়োজন।")
            await app.send_video(
                chat_id=user_id, video=new_path, duration=video_dur,
                thumb=data["thumb"], caption=f"✅ `{new_name}`",
                progress=progress_bar, progress_args=("📤 সরাসরি আপলোড...", status_msg, last_update_time)
            )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        if os.path.exists(data["dir"]): shutil.rmtree(data["dir"])
        if user_id in user_data: del user_data[user_id]

# ==============================================================================
# --- ৯. রানার ---
# ==============================================================================

async def start_services():
    print("সার্ভার সিস্টেম চালু হচ্ছে...")
    await app.start()
    if user_app:
        try: await user_app.start()
        except: pass
    print("বট এখন অনলাইন! 🚀")
    await idle()
    await app.stop()
    if user_app: await user_app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())
