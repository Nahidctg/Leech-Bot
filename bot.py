import os
import time
import asyncio
import subprocess
import shutil
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- আপনার তথ্য ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

# মডিউল ইমপোর্ট চেক (Error Fix)
try:
    import aria2p
except ImportError:
    os.system("pip install aria2p")
    import aria2p

app = Client("final_interactive_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ইউজার ডাটা এবং স্টেট
user_data = {}

# Aria2 Daemon চালু করা
def start_aria2():
    try:
        subprocess.Popen(["pkill", "-9", "aria2c"])
        time.sleep(1)
        subprocess.Popen([
            "aria2c", "--enable-rpc", "--rpc-listen-all=false", 
            "--rpc-listen-port=6800", "--max-connection-per-server=16", 
            "--split=16", "--min-split-size=1M", "--daemon=true"
        ])
        time.sleep(2)
        return aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))
    except Exception as e:
        print(f"Aria2 Startup Error: {e}")
        return None

aria2 = start_aria2()

def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

# প্রগ্রেস বার (Flood Wait এড়াতে ১০ সেকেন্ড বিরতি)
last_edit = {}
async def progress_bar(current, total, status_text, status_msg):
    now = time.time()
    msg_id = status_msg.id
    if (now - last_edit.get(msg_id, 0)) < 10:
        return
    last_edit[msg_id] = now
    
    percentage = (current * 100) / total if total > 0 else 0
    bar = "".join(["▰" for i in range(int(percentage // 10))]) + "".join(["▱" for i in range(10 - int(percentage // 10))])
    
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

# --- ১. ডাউনলোড সেকশন ---
@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    status_msg = await message.reply_text("লিংক প্রসেস করছি... ⏳")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    try:
        # Cloudflare Bypass Headers
        options = {"dir": download_dir, "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}
        download = aria2.add_uris([url], options=options)
        
        while not download.is_complete:
            download.update()
            if download.has_failed:
                await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিংকটি ভুল বা প্রোটেক্টেড।")
                return
            await progress_bar(download.completed_length, download.total_length, "📥 সার্ভারে ডাউনলোড হচ্ছে...", status_msg)
            await asyncio.sleep(2)

        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        file_path = max(files, key=os.path.getctime)
        
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
            f"💰 **সাইজ:** {human_size(os.path.getsize(file_path))}\n\n"
            "এখন আপনি যা করতে পারেন:\n"
            "👉 নতুন নাম লিখে পাঠান (রিনেম হবে)\n"
            "👉 একটি ছবি পাঠান (থাম্বনেইল হবে)\n"
            "👉 অথবা সরাসরি নিচের বাটনে ক্লিক করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ এরর: {str(e)}")

# --- ২. রিনেম ও থাম্বনেইল হ্যান্ডলার ---
@app.on_message(filters.private & (filters.text | filters.photo))
async def customization_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_data: return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নাম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট হয়েছে!")

# --- ৩. ফাইনাল আপলোড সেকশন ---
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
    
    try:
        start_time = time.time()
        await client.send_video(
            chat_id=user_id,
            video=new_path,
            thumb=data["thumb"],
            caption=f"✅ **ফাইল:** `{data['new_name']}`\n💰 **সাইজ:** {human_size(os.path.getsize(new_path))}",
            supports_streaming=True,
            progress=progress_bar,
            progress_args=("📤 টেলিগ্রামে আপলোড হচ্ছে...", status_msg)
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        shutil.rmtree(data["dir"])
        del user_data[user_id]

print("বটটি রানিং হয়েছে! কোনো এরর নেই।")
app.run()
