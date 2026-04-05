# ==============================================================================
# --- প্রফেশনাল টেলিগ্রাম আলটিমেট ডাউনলোড ও আপলোড সিস্টেম (Version 4.0) ---
# --- ফিচার: স্মার্ট বাইপাস ENGINE, ৪জিবি প্রিমিয়াম সাপোর্ট, হাইব্রিড মোড ---
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
# --- ১. গ্লোবাল কনফিগারেশন এবং এপিআই সেটিংস ---
# ==============================================================================

# আপনার টেলিগ্রাম এপিআই এবং বট টোকেন (নিচে সঠিক তথ্য দিন)
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# --- প্রিমিয়াম ইউজার সেশন সেটিংস (4GB Support) ---
# যদি ৪জিবি সাপোর্ট চান তবে এখানে আপনার প্রিমিয়াম সেশন কোড দিন।
# যদি আপাতত না থাকে তবে শুধু "" (খালি) রাখুন। বট তবুও রেসপন্স করবে।
STRING_SESSION = "" 

# সেশন ব্যবহার করলে অবশ্যই একটি প্রাইভেট চ্যানেলের আইডি দিন যেখানে বট এবং ইউজার অ্যাডমিন।
# এটি অবশ্যই -100 দিয়ে শুরু হওয়া ১৩ সংখ্যার আইডি হতে হবে।
LOG_CHANNEL = -1002491365982 

# ==============================================================================
# --- ২. ক্লায়েন্ট ইনিশিয়ালাইজেশন (Bot & User Session) ---
# ==============================================================================

# মূল বট ক্লায়েন্ট (এটি ইউজারের সাথে কথা বলবে)
app = Client(
    "power_bot_instance", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    workers=100  # মাল্টি-টাস্কিংয়ের জন্য ১০০টি ওয়ার্কার
)

# প্রিমিয়াম ইউজার ক্লায়েন্ট (এটি শুধু ৪জিবি আপলোডের জন্য)
user_app = None
if STRING_SESSION and len(STRING_SESSION) > 10:
    try:
        user_app = Client(
            "premium_user_session", 
            api_id=API_ID, 
            api_hash=API_HASH, 
            session_string=STRING_SESSION
        )
        print("প্রিমিয়াম ইউজার সেশন ক্লায়েন্ট কনফিগার করা হয়েছে। ✅")
    except Exception as e:
        print(f"সেশন কনফিগারেশন এরর: {e}")

# ডাউনলোড ডেটা সাময়িকভাবে রাখার জন্য ডিকশনারি
user_data = {}

# ==============================================================================
# --- ৩. সাহায্যকারী ফাংশনসমূহ (Core Utility Logic) ---
# ==============================================================================

def human_size(num):
    """ফাইলের সাইজকে মানুষের পড়ার উপযোগী ফরম্যাটে রূপান্তর করে।"""
    if not num:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

def get_duration(file_path):
    """ভিডিও ফাইলের মেটাডেটা থেকে সঠিক ডিউরেশন বের করে।"""
    try:
        # হাচোয়ার দিয়ে ভিডিওর সময় বের করা হচ্ছে
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception as e:
        print(f"ডিউরেশন এক্সট্রাকশন এরর: {e}")
    return 0

# ==============================================================================
# --- ৪. স্মার্ট লিঙ্ক বাইপাস ইঞ্জিন (Smart AI Engine) ---
# ==============================================================================

async def get_smart_link(url):
    """
    এটি একটি অত্যন্ত শক্তিশালী বাইপাস ফাংশন।
    এটি মুভি গেটওয়ে (movielinkbd, drivecloud) এবং শর্টনার লিঙ্ক বাইপাস করে।
    """
    print(f"লিঙ্ক এনালাইসিস হচ্ছে: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': url,
        'Connection': 'keep-alive'
    }

    # ১. রিডাইরেক্ট এবং কুউকি ফলো করা
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        # রিডাইরেক্ট ফলো করে আসল গন্তব্য খুঁজে বের করা হচ্ছে
        response = session.get(url, allow_redirects=True, timeout=12, stream=True)
        final_url = response.url
        
        # যদি সরাসরি ফাইল ফরম্যাট (MKV, MP4, ZIP) পাওয়া যায়
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi']):
            print(f"আসল ফাইল লিঙ্ক পাওয়া গেছে: {final_url}")
            return final_url
        
        url = final_url # রিডাইরেক্ট হওয়া ইউআরএল নিয়ে পরবর্তী ধাপে যাওয়া
    except Exception as e:
        print(f"রিডাইরেক্ট চেক এরর: {e}")

    # ২. YT-DLP ব্যবহার করে ডিপ স্ক্যান করা
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'noplaylist': True,
        'user_agent': headers['User-Agent']
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # ভিডিও বা ক্লাউড সাইটের ভেতর থেকে আসল স্ট্রিমিং লিঙ্ক বের করা হচ্ছে
            info = ydl.extract_info(url, download=False)
            smart_url = info.get('url', url)
            print(f"স্মার্ট ইঞ্জিন সফল: {smart_url}")
            return smart_url
        except Exception as e:
            print(f"স্মার্ট ইঞ্জিন ফেইল: {e}. অরিজিনাল লিঙ্ক ব্যবহার করা হচ্ছে।")
            return url

# ==============================================================================
# --- ৫. প্রগ্রেস বার ফাংশন (আপনার অরিজিনাল ডিটেইলড স্টাইল) ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    """ডাউনলোড এবং আপলোড উভয়ের জন্য আপনার অরিজিনাল বিস্তারিত প্রগ্রেস বার।"""
    now = time.time()
    # টেলিগ্রাম ফ্লাড ওয়েট এড়াতে ৫ সেকেন্ড পরপর আপডেট করা হবে
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    percentage = (current * 100) / total if total > 0 else 0
    bar_length = 12 # বারের দৈর্ঘ্য কিছুটা বাড়ানো হয়েছে
    filled_length = int(percentage // (100 / bar_length))
    bar = "▰" * filled_length + "▱" * (bar_length - filled_length)
    
    try:
        # মেসেজ আপডেট করে স্ট্যাটাস দেখানো
        await status_msg.edit_text(
            f"**{status_text}**\n\n"
            f"🌀 `{bar}` **{round(percentage, 2)}%**\n"
            f"📦 সাইজ: `{human_size(current)}` / `{human_size(total)}`"
        )
    except Exception:
        pass

# ==============================================================================
# --- ৬. বট মেসেজ হ্যান্ডলারসমূহ (The Core Handlers) ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    """বট স্টার্ট কমান্ড হ্যান্ডলার (রেসপন্স চেক করার জন্য প্রিন্ট সহ)"""
    print(f"Start কমান্ড এসেছে ইউজারের কাছ থেকে: {message.from_user.id}")
    
    mode_text = "প্রিমিয়াম ৪জিবি মোড সক্রিয় ✅" if user_app else "সাধারণ ২জিবি মোড সক্রিয় ⚠️"
    
    await message.reply_text(
        f"**বট অনলাইন এবং রেসপন্স করার জন্য প্রস্তুত! 🚀**\n\n"
        f"এই বটটি এখন সব ধরণের লিঙ্ক অটো-বাইপাস করে ডাউনলোড করতে পারে।\n\n"
        f"**সিস্টেম স্ট্যাটাস:**\n`{mode_text}`\n\n"
        f"যেকোনো মুভি বা ভিডিও লিঙ্ক পাঠান। আমি অটোমেটিক সেটির আসল সোর্স খুঁজে নেব।"
    )

# --- ৭. স্মার্ট ডাউনলোড সেকশন (Aria2 Engine + AI Linker) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """লিঙ্ক পাওয়ার পর অটোমেটিক বাইপাস এবং Aria2 দিয়ে ডাউনলোড।"""
    url = message.text.strip()
    user_id = message.from_user.id
    print(f"নতুন লিঙ্ক এসেছে: {url} (ইউজার: {user_id})")
    
    status_msg = await message.reply_text("স্মার্ট ইঞ্জিন লিঙ্কটি এনালাইসিস করছে... 🔎")
    
    # অটো বাইপাসিং লেয়ার ব্যবহার করে লিঙ্ক বের করা
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("আসল লিঙ্ক পাওয়া গেছে। সার্ভারে হাই-স্পিড ডাউনলোড শুরু হচ্ছে... 📥")
    
    # ইউজারের জন্য ইউনিক ডিরেক্টরি তৈরি
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # ব্রাউজার ইউজার এজেন্ট
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        # Aria2 কমান্ড সেটআপ (ডিটেইলড কনফিগারেশন)
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "--split=16",
            "--summary-interval=1",
            "--user-agent", ua,
            "--referer", url,
            "--check-certificate=false",
            direct_link
        ]

        # Aria2 সাব-প্রসেস রান করা
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        last_update_time = [0]
        
        # আউটপুট থেকে প্রগ্রেস রিড করা (আপনার অরিজিনাল লজিক)
        while True:
            line = await process.stdout.readline()
            if not line: break
            
            line_str = line.decode().strip()
            
            # প্রগ্রেস এবং সাইজ রিড করার জন্য Regex
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
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে! লিঙ্কটি সম্ভবত বিজ্ঞাপনের আড়ালে ঢাকা অথবা এক্সপায়ার হয়ে গেছে।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # আপলোডের জন্য ডেটা স্টোর করা
        user_data[user_id] = {
            "file_path": file_path,
            "new_name": os.path.basename(file_path),
            "thumb": None,
            "dir": download_dir
        }

        await status_msg.delete()
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n"
            f"📄 **ফাইল:** `{os.path.basename(file_path)}` \n"
            f"💰 **সাইজ:** `{human_size(file_size)}` \n\n"
            "নাম বা থাম্বনেইল সেট করে নিচের বাটনে ক্লিক করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ সিস্টেম এরর: {str(e)}")

# --- ৮. রিনেম ও থাম্বনেইল হ্যান্ডলার (আপনার অরিজিনাল ডিটেইলড লজিক) ---

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    """ইউজার নাম পাঠালে সেটি ফাইল নেমে সেট করবে এবং ফটো পাঠালে থাম্বনেইল নেবে।"""
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 ফাইল নেম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট করা হয়েছে!")

# --- ৯. আপলোড সেকশন (The 4GB Hybrid Logic) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    """আপলোড বাটনে ক্লিক করলে হাইব্রিড সিস্টেমে ফাইল পাঠানো।"""
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("তথ্য পাওয়া যায়নি! আবার লিঙ্ক দিন।", show_alert=True)
        return

    data = user_data[user_id]
    old_path = data["file_path"]
    new_path = os.path.join(os.path.dirname(old_path), data["new_name"])
    os.rename(old_path, new_path)
    
    file_size = os.path.getsize(new_path)
    status_msg = await callback_query.message.edit_text("📤 আপলোড শুরু করার প্রস্তুতি নিচ্ছি...")
    
    video_dur = get_duration(new_path)
    last_update_time = [0]

    try:
        # কন্ডিশন: ৪জিবি প্রিমিয়াম মোড (যদি সেশন থাকে)
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL,
                video=new_path,
                duration=video_dur,
                thumb=data["thumb"],
                caption=f"✅ **ফাইল:** `{data['new_name']}`",
                supports_streaming=True,
                progress=progress_bar,
                progress_args=("📤 প্রিমিয়াম আপলোড...", status_msg, last_update_time)
            )
            
            # লগ চ্যানেল থেকে ইউজারের ইনবক্সে কপি করা
            await app.copy_message(
                chat_id=user_id,
                from_chat_id=LOG_CHANNEL,
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(file_size)}"
            )
        
        # কন্ডিশন: সাধারণ বট মোড (২জিবি লিমিট)
        else:
            if file_size > 2000 * 1024 * 1024:
                await status_msg.edit_text("❌ ফাইলটি ২জিবির বড়! এটি আপলোড করতে প্রিমিয়াম সেশন লাগবে।")
                return
            
            await status_msg.edit_text("📤 সাধারণ ২জিবি মোডে আপলোড হচ্ছে...")
            await app.send_video(
                chat_id=user_id,
                video=new_path,
                duration=video_dur,
                thumb=data["thumb"],
                caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(file_size)}",
                supports_streaming=True,
                progress=progress_bar,
                progress_args=("📤 সরাসরি আপলোড হচ্ছে...", status_msg, last_update_time)
            )

        await status_msg.delete()
        print(f"সফল আপলোড: {data['new_name']}")
    
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
        print(f"আপলোড এরর ডিটেইল: {e}")
    
    finally:
        # কাজ শেষে ডিরেক্টরি পরিষ্কার করা
        if os.path.exists(data["dir"]):
            shutil.rmtree(data["dir"])
        if user_id in user_data:
            del user_data[user_id]

# ==============================================================================
# --- ১০. সিস্টেম স্টার্টার (The Secure Running Engine) ---
# ==============================================================================

async def start_services():
    """বট এবং প্রিমিয়াম ইউজার সেশন ক্লায়েন্ট একসাথে স্টার্ট করার প্রফেশনাল মেথড।"""
    print("-" * 40)
    print("সার্ভার সিস্টেম চালু হচ্ছে...")
    print("-" * 40)
    
    # ১. মূল বট ক্লায়েন্ট স্টার্ট করা
    await app.start()
    print("মূল বট ক্লায়েন্ট স্টার্ট হয়েছে! ✅")
    
    # ২. প্রিমিয়াম ইউজার সেশন স্টার্ট করা (যদি থাকে)
    if user_app:
        try:
            await user_app.start()
            print("প্রিমিয়াম ইউজার সেশন ক্লায়েন্ট স্টার্ট হয়েছে! (4GB Enabled) ✅")
        except Exception as e:
            print(f"প্রিমিয়াম সেশন স্টার্ট করতে ব্যর্থ: {e}")
            print("সতর্কতা: বটটি এখন শুধুমাত্র ২জিবি সাধারণ মোডে চলবে।")
    
    print("-" * 40)
    print("অভিনন্দন! বট এখন পুরোপুরি অনলাইন এবং রেসপন্স করার জন্য প্রস্তুত! 🚀")
    print("-" * 40)
    
    # ৩. বটকে রানিং রাখা এবং কমান্ডের জন্য অপেক্ষা করা
    await idle()
    
    # ৪. বন্ধ করার সময় ক্লায়েন্টদের স্টপ করা
    await app.stop()
    if user_app:
        await user_app.stop()

if __name__ == "__main__":
    # ইভেন্ট লুপের মাধ্যমে সার্ভিস রান করা
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        print("\nবট ম্যানুয়ালি বন্ধ করা হয়েছে।")
