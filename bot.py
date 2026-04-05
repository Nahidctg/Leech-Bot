import os
import time
import asyncio
import subprocess
import shutil
import re
import requests  # রিডাইরেক্ট এবং মুভি গেটওয়ে লিঙ্ক চেক করার জন্য
import yt_dlp    # স্মার্টলি ভিডিও লিঙ্ক এক্সট্রাক্ট করার জন্য
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# ==========================================
# --- ১. আপনার কনফিগারেশন সেকশন (Config) ---
# ==========================================

# আপনার টেলিগ্রাম API এর তথ্যগুলো এখানে দিন
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# --- প্রিমিয়াম ইউজার সেশন এবং চ্যানেল আইডি ---
# যদি ৪জিবি সাপোর্ট চান তবে STRING_SESSION দিন, নাহলে খালি "" রাখুন।
STRING_SESSION = "" 
# সেশন ব্যবহার করলে অবশ্যই একটি প্রাইভেট চ্যানেলের আইডি দিন যেখানে বট অ্যাডমিন।
LOG_CHANNEL = -1002491365982 

# ==========================================
# --- ২. ক্লায়েন্ট ইনিশিয়ালাইজেশন (Clients) ---
# ==========================================

# সাধারণ বট ক্লায়েন্ট (Account A)
app = Client(
    "final_interactive_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

# প্রিমিয়াম ইউজার ক্লায়েন্ট (Account B - যদি সেশন থাকে)
user_app = None
if STRING_SESSION:
    user_app = Client(
        "premium_user_session", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

# ইউজারের ডাউনলোড ফাইল এবং সেটিংস স্টোর করার জন্য ডিকশনারি
user_data = {}

# ==========================================
# --- ৩. সাহায্যকারী ফাংশন (Helper Funcs) ---
# ==========================================

def human_size(num):
    """ফাইলের সাইজকে মানুষের পড়ার উপযোগী ফরম্যাটে রূপান্তর করে।"""
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

def get_duration(file_path):
    """ভিডিও ফাইলের সঠিক সময় বা ডিউরেশন বের করে।"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception: 
        pass
    return 0

def get_smart_link(url):
    """
    এই ফাংশনটি আপনার দেওয়া movielinkbd বা drivecloud লিঙ্ক থেকে 
    ব্রাউজারের মতো আসল ডাইরেক্ট ডাউনলোড লিঙ্কটি খুঁজে বের করবে।
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Referer': url
    }
    
    # প্রথমে রিডাইরেক্ট (Redirect) চেক করা মুভি গেটওয়ে লিঙ্কের জন্য
    try:
        # requests ব্যবহার করে আসল গন্তব্য খুঁজে বের করা হচ্ছে
        response = requests.head(url, allow_redirects=True, headers=headers, timeout=10)
        final_url = response.url
        
        # যদি লিঙ্কটি সরাসরি ফাইল হয় তবে এটিই ফেরত দিবে
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov']):
            return final_url
        url = final_url # রিডাইরেক্টেড ইউআরএল নিয়ে yt-dlp তে পাঠানো হবে
    except Exception:
        pass

    # yt-dlp ব্যবহার করে ভিডিও লিঙ্ক বা ড্রাইভ লিঙ্ক চেক করা
    ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best', 'noplaylist': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('url', url)
        except Exception:
            # যদি কোনোটিই কাজ না করে তবে অরিজিনাল লিঙ্কই ফেরত দিবে
            return url

# ==========================================
# --- ৪. প্রগ্রেস বার ফাংশন (Progress Bar) ---
# ==========================================

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    """ডাউনলোড এবং আপলোড চলাকালীন প্রগ্রেস বার আপডেট করে।"""
    now = time.time()
    # ৫ সেকেন্ড পর পর আপডেট হবে যাতে টেলিগ্রাম ফ্লাড ওয়েট (Flood Wait) না দেয়
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
            f"🌀 {bar} {round(percentage, 2)}%\n"
            f"📦 প্রগ্রেস: {human_size(current)} / {human_size(total)}"
        )
    except Exception:
        pass

# ==========================================
# --- ৫. মেসেজ হ্যান্ডলার সেকশন (Handlers) ---
# ==========================================

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    """বট স্টার্ট করার পর স্বাগতম মেসেজ এবং মোড চেক।"""
    mode = "Premium (4GB Supported) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    await message.reply_text(
        f"বট অনলাইন! 🚀\n\n"
        f"**বর্তমান স্ট্যাটাস:** `{mode}`\n\n"
        f"আপনার মুভি বা ফাইলের ডাইরেক্ট লিঙ্ক পাঠান। আমি সেটি স্মার্টলি ডাউনলোড করে দেব।"
    )

# --- ৬. ডাউনলোড সেকশন (Aria2 + Smart Resolver) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    """লিঙ্ক পাওয়া মাত্র ডাউনলোড প্রসেস শুরু করবে।"""
    url = message.text.strip()
    user_id = message.from_user.id
    status_msg = await message.reply_text("লিঙ্কটি স্মার্টলি এনালাইসিস করছি... 🔎")
    
    # মুভি লিঙ্ক বা ড্রাইভ লিঙ্কের গেটওয়ে বাইপাস করে ডাইরেক্ট লিঙ্ক বের করা
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("সার্ভারে ডাউনলোড করার প্রস্তুতি নিচ্ছি... ⏳")
    
    # ইউনিক ডাউনলোড ফোল্ডার তৈরি করা
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): 
        os.makedirs(download_dir)

    try:
        # Aria2 কমান্ড সেটআপ (আপনার অরিজিনাল কমান্ড)
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "--split=16",
            "--summary-interval=1",
            "--user-agent", "Mozilla/5.0",
            direct_link
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        last_update_time = [0]
        
        # Aria2 এর আউটপুট রিড করে প্রগ্রেস দেখানো
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            line_str = line.decode().strip()
            
            # প্রগ্রেস পার্সেন্টেজ রিড করা
            match = re.search(r'\((\d+)%\)', line_str)
            if match:
                percentage = int(match.group(1))
                size_match = re.search(r'(\d+(?:\.\d+)?\w+)/(\d+(?:\.\d+)?\w+)', line_str)
                
                if size_match:
                    current_size_str = size_match.group(1)
                    total_size_str = size_match.group(2)
                    
                    now = time.time()
                    if (now - last_update_time[0]) > 5:
                        last_update_time[0] = now
                        bar = "▰" * (percentage // 10) + "▱" * (10 - (percentage // 10))
                        try:
                            await status_msg.edit_text(
                                f"**📥 সার্ভারে ডাউনলোড হচ্ছে...**\n\n"
                                f"🌀 {bar} {percentage}%\n"
                                f"📦 প্রগ্রেস: {current_size_str} / {total_size_str}"
                            )
                        except: pass

        await process.wait()

        # ডাউনলোড শেষ হওয়ার পর আসল ফাইলটি খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিঙ্কটি ডাইরেক্ট ডাউনলোড সাপোর্ট করছে না।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # ইউজার ডেটা সাময়িকভাবে সেভ করা
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
            "নাম বা থাম্বনেইল পরিবর্তন করতে পারেন, অথবা সরাসরি আপলোড করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ একটি ত্রুটি দেখা দিয়েছে: {str(e)}")

# --- ৭. রিনেম ও থাম্বনেইল হ্যান্ডলার (Customization) ---

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    """ইউজার নাম পাঠালে সেটি ফাইল নেমে সেট করবে এবং ফটো পাঠালে থাম্বনেইল হিসেবে নেবে।"""
    user_id = message.from_user.id
    if user_id not in user_data: return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন ফাইল নেম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সফলভাবে সেট হয়েছে!")

# --- ৮. আপলোড সেকশন (Hybrid 4GB Support Logic) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    """আপলোড বাটনে ক্লিক করলে ফাইলটি টেলিগ্রামে পাঠাবে।"""
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ফাইল তথ্য খুঁজে পাওয়া যায়নি!", show_alert=True)
        return

    data = user_data[user_id]
    old_path = data["file_path"]
    new_path = os.path.join(os.path.dirname(old_path), data["new_name"])
    
    # ফাইল রিনেম করা
    os.rename(old_path, new_path)
    file_size = os.path.getsize(new_path)
    
    status_msg = await callback_query.message.edit_text("📤 টেলিগ্রামে আপলোড শুরু হচ্ছে...")
    video_duration = get_duration(new_path)
    last_update_time = [0]

    try:
        # কন্ডিশন ১: যদি প্রিমিয়াম সেশন থাকে তবে ৪জিবি মোডে আপলোড হবে
        if user_app:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
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
            # লগ চ্যানেল থেকে ইউজারকে ফাইলটি ফরোয়ার্ড করা
            await app.copy_message(
                chat_id=user_id,
                from_chat_id=LOG_CHANNEL,
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(file_size)}"
            )
        
        # কন্ডিশন ২: সেশন না থাকলে সাধারণ ২জিবি মোড
        else:
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

        await status_msg.delete()
    
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড ত্রুটি: {str(e)}")
    
    finally:
        # কাজ শেষে সার্ভার থেকে ফাইল এবং ফোল্ডার মুছে ফেলা
        if os.path.exists(data["dir"]): 
            shutil.rmtree(data["dir"])
        if user_id in user_data: 
            del user_data[user_id]

# ==========================================
# --- ৯. সার্ভিস স্টার্ট সেকশন (Execution) ---
# ==========================================

async def start_services():
    """বট এবং ইউজার ক্লায়েন্ট একসাথে চালু করার ফাংশন।"""
    print("সার্ভিস স্টার্ট হচ্ছে...")
    await app.start()
    
    if user_app:
        await user_app.start()
        print("প্রিমিয়াম ইউজার সেশন সক্রিয়। ৪জিবি ফাইল সাপোর্ট করবে।")
    else:
        print("সাধারণ মোড সক্রিয়। ২জিবি ফাইল সাপোর্ট করবে।")
        
    print("বট এখন রানিং! 🚀")
    # ইনফিনিট লুপে রাখা যাতে বট বন্ধ না হয়
    await asyncio.Event().wait()

if __name__ == "__main__":
    # পাইথন ইভেন্ট লুপের মাধ্যমে স্টার্ট করা
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        print("বট বন্ধ করা হয়েছে।")
