import os
import time
import asyncio
import subprocess
import shutil
import re  # আপনার অরিজিনাল ইমপোর্ট
import yt_dlp  # স্মার্ট লিঙ্ক প্রসেস করার জন্য নতুন যোগ করা হয়েছে
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# --- ১. আপনার কনফিগারেশন সেকশন ---
# এখানে আপনার সঠিক তথ্যগুলো দিন
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# --- ২. প্রিমিয়াম সেশন এবং চ্যানেল আইডি (ঐচ্ছিক) ---
# যদি ৪জিবি সাপোর্ট চান তবে STRING_SESSION এ সেশন কোড দিন, নাহলে খালি "" রাখুন।
STRING_SESSION = "" 
LOG_CHANNEL = -1002345678901  # চ্যানেলে বট এবং ইউজার আইডি অ্যাডমিন থাকতে হবে।

# --- ৩. ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
# সাধারণ বট ক্লায়েন্ট (Account A)
app = Client(
    "final_interactive_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)

# প্রিমিয়াম ইউজার ক্লায়েন্ট (Account B - শুধু সেশন থাকলে চালু হবে)
user_app = None
if STRING_SESSION:
    user_app = Client(
        "premium_user_session", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

# ইউজার ডেটা স্টোর করার জন্য ডিকশনারি
user_data = {}

# --- ৪. হেল্পার ফাংশন সেকশন ---

def human_size(num):
    """বাইটকে রিডেবল ফরম্যাটে রূপান্তর করে (KB, MB, GB)"""
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

def get_duration(file_path):
    """ভিডিও ফাইলের ডিউরেশন বের করে"""
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception: 
        pass
    return 0

def get_smart_link(url):
    """
    yt-dlp ব্যবহার করে স্মার্টলি ভিডিওর ডাইরেক্ট লিঙ্ক বের করে।
    যদি সাধারণ ফাইল হয় তবে অরিজিনাল লিঙ্কই রিটার্ন করে।
    """
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'format': 'best', 
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get('url', url)
        except Exception:
            return url

# --- ৫. প্রগ্রেস বার ফাংশন (ডাউনলোড এবং আপলোড উভয়ের জন্য) ---

async def progress_bar(current, total, status_text, status_msg, last_update_time):
    now = time.time()
    # ৫ সেকেন্ড পর পর আপডেট হবে (Flood Wait এড়াতে)
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
            f"📦 সাইজ: {human_size(current)} / {human_size(total)}"
        )
    except Exception:
        pass

# --- ৬. বট কমান্ড এবং মেসেজ হ্যান্ডলার ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    # সেশন আছে কি না তার ওপর ভিত্তি করে স্ট্যাটাস দেখানো
    status = "Premium (4GB Supported) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    await message.reply_text(
        f"বট অনলাইন! 🚀\n\n"
        f"**বর্তমান মোড:** `{status}`\n"
        f"যেকোনো মুভি বা ভিডিও ডাউনলোড লিংক পাঠান।"
    )

# --- ৭. ডাউনলোড হ্যান্ডলার (Aria2 + Smart Processor) ---

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    status_msg = await message.reply_text("লিংক এনালাইসিস করছি... 🔎")
    
    # স্মার্ট লিঙ্ক প্রসেসিং
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    await status_msg.edit_text("ডাউনলোড প্রসেস শুরু হচ্ছে... ⏳")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        # Aria2 কমান্ড (আপনার অরিজিনাল স্ট্রাকচার অনুযায়ী)
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "--split=16",
            "--summary-interval=1",
            "--user-agent", user_agent,
            direct_link
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        last_update_time = [0]
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            line_str = line.decode().strip()
            
            # Aria2 এর আউটপুট থেকে পার্সেন্টিজ পার্স করা
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

        # ডাউনলোড শেষ হওয়ার পর ফাইল খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে!")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

        # ইউজার ডেটা স্টোর করা
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
            "এখন আপনি চাইলে নাম বা থাম্বনেইল পরিবর্তন করতে পারেন, অথবা সরাসরি আপলোড শুরু করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ এরর দেখা দিয়েছে: {str(e)}")

# --- ৮. রিনেম ও থাম্বনেইল হ্যান্ডলার ---

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_data: return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন নাম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট করা হয়েছে!")

# --- ৯. আপলোড সেকশন (Smart Hybrid System) ---

@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ফাইল তথ্য খুঁজে পাওয়া যায়নি!", show_alert=True)
        return

    data = user_data[user_id]
    old_path = data["file_path"]
    new_path = os.path.join(os.path.dirname(old_path), data["new_name"])
    
    os.rename(old_path, new_path)
    file_size = os.path.getsize(new_path)
    
    status_msg = await callback_query.message.edit_text("📤 টেলিগ্রামে আপলোড করার প্রস্তুতি নিচ্ছি...")
    
    video_duration = get_duration(new_path)
    last_update_time = [0]

    try:
        # যদি প্রিমিয়াম সেশন থাকে (৪জিবি মোড)
        if user_app:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম মোডে আপলোড হচ্ছে...")
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
            # চ্যানেল থেকে ইউজারের কাছে কপি করা
            await app.copy_message(
                chat_id=user_id,
                from_chat_id=LOG_CHANNEL,
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(file_size)}"
            )
        
        # যদি প্রিমিয়াম সেশন না থাকে (২জিবি মোড)
        else:
            if file_size > 2000 * 1024 * 1024:
                await status_msg.edit_text("❌ ফাইলটি ২জিবির বড়! প্রিমিয়াম সেশন ছাড়া এটি আপলোড করা অসম্ভব।")
                return
            
            await status_msg.edit_text("📤 সাধারণ ২জিবি মোডে আপলোড হচ্ছে...")
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
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    
    finally:
        # ডাউনলোড ডিরেক্টরি পরিষ্কার করা
        if os.path.exists(data["dir"]): 
            shutil.rmtree(data["dir"])
        if user_id in user_data: 
            del user_data[user_id]

# --- ১০. বট স্টার্ট করার ফাংশন (বিস্তারিত লজিক) ---

async def start_services():
    print("সার্ভিস চালু হচ্ছে...")
    # মূল বট স্টার্ট করা
    await app.start()
    # যদি সেশন থাকে তবে ইউজার সেশন স্টার্ট করা
    if user_app:
        await user_app.start()
        print("প্রিমিয়াম ইউজার সেশন সক্রিয় করা হয়েছে।")
    
    print("বট সফলভাবে রানিং! 🚀")
    # বটকে অনন্তকাল রানিং রাখা
    await asyncio.Event().wait()

if __name__ == "__main__":
    # ইভেন্ট লুপের মাধ্যমে সার্ভিস রান করা
    try:
        asyncio.run(start_services())
    except KeyboardInterrupt:
        print("বট বন্ধ করা হয়েছে।")
