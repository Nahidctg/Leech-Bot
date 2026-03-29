import os
import time
import asyncio
import subprocess
import shutil
import re  # নতুন ইমপোর্ট
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# --- আপনার সঠিক তথ্যগুলো ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("final_interactive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_data = {}

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
    except Exception: pass
    return 0

# প্রগ্রেস বার ফাংশন (ডাউনলোড এবং আপলোড উভয়ের জন্য)
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

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("বট অনলাইন! 🚀\nযেকোনো মুভি বা ফাইল ডাউনলোড লিংক পাঠান।")

# --- ডাউনলোড সেকশন (প্রগ্রেস বার সহ) ---
@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    status_msg = await message.reply_text("লিংক প্রসেস করছি... ⏳")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        # Aria2 কমান্ডে --summary-interval=1 যোগ করা হয়েছে যাতে প্রতি সেকেন্ডে স্ট্যাটাস দেয়
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "--split=16",
            "--summary-interval=1",
            "--user-agent", user_agent,
            url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        last_update_time = [0]
        
        # Aria2 এর আউটপুট রিড করে প্রগ্রেস বের করা
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            line_str = line.decode().strip()
            
            # Regex দিয়ে প্রগ্রেস পার্স করা (যেমন: [#... 12MB/45MB(26%)])
            match = re.search(r'\((\d+)%\)', line_str)
            if match:
                percentage = int(match.group(1))
                size_match = re.search(r'(\d+(?:\.\d+)?\w+)/(\d+(?:\.\d+)?\w+)', line_str)
                
                if size_match:
                    current_size_str = size_match.group(1)
                    total_size_str = size_match.group(2)
                    
                    # প্রগ্রেস আপডেট
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

        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ!")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_size = os.path.getsize(file_path)

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
            "এখন আপনি চাইলে নাম বা থাম্বনেইল পরিবর্তন করতে পারেন, অথবা সরাসরি আপলোড করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ এরর: {str(e)}")

# --- ২. রিনেম ও থাম্বনেইল হ্যান্ডলার ---
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
        await message.reply_text("🖼 থাম্বনেইল সেট হয়েছে!")

# --- ৩. আপলোড সেকশন ---
@app.on_callback_query(filters.regex("upload"))
async def upload_btn(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ফাইল পাওয়া যায়নি!", show_alert=True)
        return

    data = user_data[user_id]
    old_path = data["file_path"]
    new_path = os.path.join(os.path.dirname(old_path), data["new_name"])
    
    os.rename(old_path, new_path)
    status_msg = await callback_query.message.edit_text("📤 টেলিগ্রামে আপলোড হচ্ছে...")
    
    video_duration = get_duration(new_path)
    last_update_time = [0] # প্রগ্রেস ট্র্যাকিংয়ের জন্য

    try:
        await client.send_video(
            chat_id=user_id,
            video=new_path,
            duration=video_duration,
            thumb=data["thumb"],
            caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(os.path.getsize(new_path))}",
            supports_streaming=True,
            progress=progress_bar,
            progress_args=("📤 টেলিগ্রামে আপলোড হচ্ছে...", status_msg, last_update_time)
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        if os.path.exists(data["dir"]): shutil.rmtree(data["dir"])
        if user_id in user_data: del user_data[user_id]

print("বট রানিং...")
app.run()
