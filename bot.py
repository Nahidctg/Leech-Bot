# ==========================================
# --- প্রফেশনাল টেলিগ্রাম ডাউনলোড ও আপলোড বট ---
# --- ফিচার: স্মার্ট বাইপাস, ৪জিবি সাপোর্ট, হাইব্রিড মোড ---
# ==========================================

import os
import time
import asyncio
import subprocess
import shutil
import re
import requests
import yt_dlp
from urllib.parse import urlparse
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# ==========================================
# --- ১. কনফিগারেশন এবং এপিআই সেকশন ---
# ==========================================

# আপনার টেলিগ্রাম এপিআই এবং বট টোকেন এখানে দিন
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# --- প্রিমিয়াম সেশন কনফিগারেশন ---
# ৪জিবি সাপোর্টের জন্য STRING_SESSION দিন, না থাকলে খালি "" রাখুন।
STRING_SESSION = "" 

# সেশন ব্যবহার করলে অবশ্যই একটি প্রাইভেট চ্যানেলের আইডি দিন যেখানে বট অ্যাডমিন।
# সেশন না থাকলে এটি ০ রাখতে পারেন।
LOG_CHANNEL = -1002491365982 

# ==========================================
# --- ২. ক্লায়েন্ট ইনিশিয়ালাইজেশন (সিস্টেম কোর) ---
# ==========================================

# মূল বট ক্লায়েন্ট (Account A)
app = Client(
    "interactive_power_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

# প্রিমিয়াম ইউজার ক্লায়েন্ট (Account B) - এটি সেশন থাকলেই কেবল সক্রিয় হবে
user_app = None
if STRING_SESSION:
    user_app = Client(
        "premium_account_session", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

# ইউজারের ডাউনলোড ডেটা এবং সেটিংস সাময়িকভাবে রাখার জন্য ডিকশনারি
user_data = {}

# ==========================================
# --- ৩. সাহায্যকারী ফাংশন (Core Logic) ---
# ==========================================

def human_size(num):
    """বাইটকে মানুষের পড়ার উপযোগী ফরম্যাটে রূপান্তর করে (KB, MB, GB, TB)"""
    if not num:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

def get_duration(file_path):
    """ভিডিও ফাইলের সঠিক ডিউরেশন বা সময় বের করে (Metadata Extraction)"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception as e:
        print(f"Metadata Error: {e}")
    return 0

# ==========================================
# --- ৪. স্মার্ট লিঙ্ক বাইপাস ইঞ্জিন (Smart AI Engine) ---
# ==========================================

async def get_smart_link(url):
    """
    এটি একটি অত্যন্ত শক্তিশালী ফাংশন। এটি বিজ্ঞাপনের লিঙ্ক, শর্টনার এবং 
    মুভি গেটওয়ে (movielinkbd, drivecloud) থেকে আসল ডাইরেক্ট ডাউনলোড লিঙ্ক বের করবে।
    """
    print(f"এনালাইসিস করা হচ্ছে: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': url,
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # ১. রিডাইরেক্ট ফলো করা এবং কুকি হ্যান্ডলিং (Requests Session)
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        # রিডাইরেক্ট হওয়া পর্যন্ত অপেক্ষা করা
        response = session.get(url, allow_redirects=True, timeout=15, stream=True)
        final_url = response.url
        
        # যদি সরাসরি ফাইল ফরম্যাট পাওয়া যায় তবে সেটিই সেরা লিঙ্ক
        file_extensions = ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.mp3', '.avi', '.iso']
        if any(ext in final_url.lower() for ext in file_extensions):
            print(f"ডাইরেক্ট ফাইল লিঙ্ক পাওয়া গেছে: {final_url}")
            return final_url
        
        url = final_url # রিডাইরেক্টেড ইউআরএল নিয়ে পরবর্তী ধাপে যাওয়া
    except Exception as e:
        print(f"Redirect Analysis Error: {e}")

    # ২. yt-dlp এর মাধ্যমে ভিডিও সাইট বা ড্রাইভ সাইট চেক করা (Deep Scan)
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
            # এখানে yt-dlp ভিডিওর ভেতরের আসল স্ট্রিমিং লিঙ্কটি বের করার চেষ্টা করবে
            info = ydl.extract_info(url, download=False)
            smart_url = info.get('url', url)
            print(f"Smart Engine লিঙ্ক খুঁজে পেয়েছে: {smart_url}")
            return smart_url
        except Exception as e:
            print(f"Smart Engine Error: {e}")
            # যদি কোনোটিই কাজ না করে, তবে অরিজিনাল ইউআরএলই ফেরত দিবে যাতে Aria2c চেষ্টা করতে পারে
            return url

# ==========================================
# --- ৫. প্রগ্রেস বার ফাংশন (আপনার অরিজিনাল স্টাইল) ---
# ==========================================

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    """ডাউনলোড এবং আপলোড উভয়ের জন্য আপনার অরিজিনাল প্রগ্রেস বার লজিক।"""
    now = time.time()
    # ৫ সেকেন্ড পরপর টেলিগ্রাম মেসেজ আপডেট হবে ফ্লাড ওয়েট এড়াতে
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    # পার্সেন্টিজ এবং বার ক্যালকুলেশন
    percentage = (current * 100) / total if total > 0 else 0
    bar_length = 10
    filled_length = int(percentage // 10)
    bar = "▰" * filled_length + "▱" * (bar_length - filled_length)
    
    try:
        # মেসেজ এডিট করে ইউজারকে স্ট্যাটাস দেখানো
        await status_msg.edit_text(
            f"**{status_text}**\n\n"
            f"🌀 {bar} {round(percentage, 2)}%\n"
            f"📦 সাইজ: {human_size(current)} / {human_size(total)}\n"
            f"⏳ সময়: {time.strftime('%H:%M:%S', time.gmtime(now - last_update_time[1])) if len(last_update_time) > 1 else ''}"
        )
    except Exception:
        pass

# ==========================================
# --- ৬. বট মেসেজ হ্যান্ডলার (Handlers) ---
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    """বট স্টার্ট করার পর স্বাগতম মেসেজ এবং পাওয়ারফুল মোড চেক।"""
    print(f"Start কমান্ড দিয়েছে: {message.from_user.id}")
    
    if user_app:
        status = "পাওয়ারফুল প্রিমিয়াম মোড সক্রিয় (৪জিবি সাপোর্ট) ✅"
    else:
        status = "সাধারণ মোড সক্রিয় (২জিবি লিমিট) ⚠️"
        
    await message.reply_text(
        f"**বট অনলাইন! 🚀**\n\n"
        f"এই বটটি এখন সব ধরণের লিঙ্ক অটোমেটিক বাইপাস করতে সক্ষম।\n\n"
        f"**বর্তমান সিস্টেম স্ট্যাটাস:**\n`{status}`\n\n"
        f"যেকোনো মুভি লিঙ্ক, ড্রাইভ লিঙ্ক বা ডাইরেক্ট লিঙ্ক পাঠান। আমি নিজে থেকেই সেটির আসল ডাউনলোড সোর্স খুঁজে নেব।"
    )

# --- ৭. ডাউনলোড সেকশন (Aria2 Engine + Smart Processor) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """লিঙ্ক পাওয়ার পর অটোমেটিক বাইপাস এবং ডাউনলোড প্রসেস।"""
    url = message.text.strip()
    user_id = message.from_user.id
    
    # প্রাথমিক স্ট্যাটাস মেসেজ
    status_msg = await message.reply_text("লিঙ্কটি স্মার্ট ইঞ্জিন দিয়ে বাইপাস করছি... 🔎")
    
    # স্মার্ট লিঙ্ক ইঞ্জিন ব্যবহার করে আসল লিঙ্ক বের করা
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("আসল লিঙ্ক পাওয়া গেছে। সার্ভারে ডাউনলোড শুরু হচ্ছে... 📥")
    
    # প্রতিটি ইউজারের জন্য আলাদা ডাউনলোড ফোল্ডার
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # ব্রাউজারের মতো ইউজার এজেন্ট যাতে ব্লক না করে
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        # Aria2 কমান্ড সেটআপ (সর্বোচ্চ স্পিড এবং বাইপাস লজিক সহ)
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "--split=16",
            "--summary-interval=1",
            "--user-agent", user_agent,
            "--referer", url, # রেফারার ব্যবহার করে ৪২৯ এরর এড়ানো
            "--check-certificate=false",
            "--connect-timeout=60",
            direct_link
        ]

        # সাব-প্রসেস চালু করা Aria2c এর জন্য
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # প্রগ্রেস ট্র্যাকিংয়ের জন্য টাইম স্ট্যাম্প
        last_update_time = [0, time.time()]
        
        # Aria2 এর আউটপুট লাইন বাই লাইন পড়া (আপনার অরিজিনাল লজিক)
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            line_str = line.decode().strip()
            
            # Regex ব্যবহার করে পার্সেন্টিজ এবং সাইজ বের করা
            match = re.search(r'\((\d+)%\)', line_str)
            if match:
                percentage = int(match.group(1))
                size_match = re.search(r'(\d+(?:\.\d+)?\w+)/(\d+(?:\.\d+)?\w+)', line_str)
                
                if size_match:
                    current_sz = size_match.group(1)
                    total_sz = size_match.group(2)
                    
                    # ৫ সেকেন্ড অন্তর অন্তর টেলিগ্রামে আপডেট পাঠানো
                    now = time.time()
                    if (now - last_update_time[0]) > 5:
                        last_update_time[0] = now
                        bar = "▰" * (percentage // 10) + "▱" * (10 - (percentage // 10))
                        try:
                            await status_msg.edit_text(
                                f"**📥 সার্ভারে ডাউনলোড হচ্ছে...**\n\n"
                                f"🌀 {bar} {percentage}%\n"
                                f"📦 প্রগ্রেস: {current_sz} / {total_sz}\n"
                                f"🚀 স্পিড: হাই-স্পিড ডাউনলোড"
                            )
                        except:
                            pass

        # প্রসেস শেষ হওয়ার জন্য অপেক্ষা করা
        await process.wait()

        # ডাউনলোড হওয়া ফাইলটি খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি সম্ভবত বিজ্ঞাপনে ভরা অথবা এক্সপায়ার হয়ে গেছে।")
            return
        
        # সবচেয়ে নতুন ফাইলটি বেছে নেওয়া
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # ইউজার ডেটা স্টোর করা আপলোডের জন্য
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
            f"💰 **সাইজ:** {human_size(file_size)}\n\n"
            "নাম বা থাম্বনেইল সেট করে আপলোড বাটনে ক্লিক করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ একটি সিস্টেম এরর দেখা দিয়েছে: {str(e)}")

# --- ৮. রিনেম ও থাম্বনেইল হ্যান্ডলার (আপনার অরিজিনাল লজিক) ---

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    """ইউজার নাম পাঠালে সেটি ফাইল নেমে সেট করবে এবং ফটো পাঠালে থাম্বনেইল হিসেবে নেবে।"""
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন ফাইল নেম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সফলভাবে সেট হয়েছে!")

# --- ৯. আপলোড সেকশন (সুপার স্মার্ট হাইব্রিড মোড) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    """আপলোড বাটনে ক্লিক করলে ফাইলটি টেলিগ্রামে পাঠানোর প্রসেস।"""
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ফাইল তথ্য খুঁজে পাওয়া যায়নি! আবার লিঙ্ক দিন।", show_alert=True)
        return

    data = user_data[user_id]
    old_path = data["file_path"]
    new_path = os.path.join(os.path.dirname(old_path), data["new_name"])
    
    # ফাইলটি রিনেম করা
    os.rename(old_path, new_path)
    file_size = os.path.getsize(new_path)
    
    status_msg = await callback_query.message.edit_text("📤 টেলিগ্রামে আপলোড করার প্রস্তুতি নিচ্ছি...")
    
    # ভিডিও ডিউরেশন বের করা
    video_duration = get_duration(new_path)
    # প্রসেস ট্র্যাকিং টাইম
    last_update_time = [0, time.time()]

    try:
        # কন্ডিশন ১: যদি প্রিমিয়াম সেশন (STRING_SESSION) সেট করা থাকে
        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে ব্যবহার করে আপলোড হচ্ছে...")
            
            # প্রিমিয়াম সেশন দিয়ে প্রথমে লগ চ্যানেলে আপলোড করা
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL,
                video=new_path,
                duration=video_duration,
                thumb=data["thumb"],
                caption=f"✅ **ফাইল:** `{data['new_name']}`",
                supports_streaming=True,
                progress=progress_bar,
                progress_args=("📤 প্রিমিয়াম আপলোড...", status_msg, last_update_time)
            )
            
            # এবার মূল বট দিয়ে চ্যানেল থেকে ইউজারের কাছে ফাইলটি কপি করে পাঠানো
            await app.copy_message(
                chat_id=user_id,
                from_chat_id=LOG_CHANNEL,
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(file_size)}"
            )
        
        # কন্ডিশন ২: যদি প্রিমিয়াম সেশন না থাকে (সাধারণ বট মোড)
        else:
            # ২জিবি লিমিট চেক করা
            if file_size > 2000 * 1024 * 1024:
                await status_msg.edit_text("❌ ফাইলটি ২জিবির বড়! এটি পাঠানোর জন্য প্রিমিয়াম সেশন প্রয়োজন।")
                return
            
            await status_msg.edit_text("📤 সাধারণ ২জিবি মোডে সরাসরি আপলোড হচ্ছে...")
            await app.send_video(
                chat_id=user_id,
                video=new_path,
                duration=video_duration,
                thumb=data["thumb"],
                caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(file_size)}",
                supports_streaming=True,
                progress=progress_bar,
                progress_args=("📤 সাধারণ আপলোড...", status_msg, last_update_time)
            )

        # আপলোড শেষে স্ট্যাটাস মেসেজ ডিলিট করা
        await status_msg.delete()
        print(f"সফলভাবে আপলোড হয়েছে: {data['new_name']}")
    
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড করার সময় এরর হয়েছে: {str(e)}")
        print(f"Upload Error: {e}")
    
    finally:
        # কাজ শেষ হওয়ার পর সার্ভার থেকে ডাউনলোড ফোল্ডারটি মুছে ফেলা
        if os.path.exists(data["dir"]):
            shutil.rmtree(data["dir"])
        # ইউজারের টেম্পোরারি ডেটা মুছে ফেলা
        if user_id in user_data:
            del user_data[user_id]

# ==========================================
# --- ১০. সার্ভিস স্টার্ট সেকশন (System Runner) ---
# ==========================================

async def start_services():
    """বট এবং প্রিমিয়াম সেশন ক্লায়েন্ট একসাথে প্রফেশনালভাবে চালু করার ফাংশন।"""
    print("-" * 30)
    print("সিস্টেম চালু হচ্ছে...")
    
    # মূল বট চালু করা
    await app.start()
    print("বট ক্লায়েন্ট সক্রিয়! ✅")
    
    # সেশন থাকলে প্রিমিয়াম ইউজার সেশন চালু করা
    if user_app:
        try:
            await user_app.start()
            print("প্রিমিয়াম ইউজার সেশন সক্রিয়! (৪জিবি সাপোর্ট পাওয়া যাবে) ✅")
        except Exception as e:
            print(f"সেশন স্টার্ট এরর: {e}. বট সাধারণ মোডে চলবে।")
    
    print("-" * 30)
    print("বট এখন পুরোপুরি অনলাইন এবং রেসপন্স করার জন্য তৈরি! 🚀")
    print("-" * 30)
    
    # বটকে অনন্তকাল রানিং রাখার জন্য ওয়েট করা
    await asyncio.Event().wait()

if __name__ == "__main__":
    # পাইথন ইভেন্ট লুপের মাধ্যমে সার্ভিস রান করা
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        print("\nবট বন্ধ করা হয়েছে।")
