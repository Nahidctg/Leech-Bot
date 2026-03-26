import os
import time
import asyncio
import subprocess
import shutil
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aria2p

# --- আপনার তথ্য ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("interactive_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ইউজার ডেটা স্টোর করার জন্য (ডাউনলোড করা ফাইলের তথ্য রাখার জন্য)
user_data = {}

# Aria2 RPC সেটআপ
try:
    subprocess.Popen(["pkill", "-9", "aria2c"])
    time.sleep(1)
    subprocess.Popen(["aria2c", "--enable-rpc", "--rpc-listen-all=false", "--rpc-listen-port=6800", "--max-connection-per-server=16", "--split=16", "--daemon=true"])
    time.sleep(2)
    aria2_client = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))
except Exception as e:
    print(f"Aria2 Error: {e}")

def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

# প্রগ্রেস বার
last_edit_time = {}
async def update_progress(current, total, status_text, status_msg):
    msg_id = status_msg.id
    now = time.time()
    if (now - last_edit_time.get(msg_id, 0)) < 8: return
    last_edit_time[msg_id] = now
    percentage = (current * 100) / total if total > 0 else 0
    bar = "".join(["▰" for i in range(int(percentage // 10))]) + "".join(["▱" for i in range(10 - int(percentage // 10))])
    try: await status_msg.edit_text(f"**{status_text}**\n\n🔰 {bar} {round(percentage, 2)}%\n📦 {human_size(current)} / {human_size(total)}")
    except: pass

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("বট অনলাইন! 🚀\nডাউনলোড শুরু করতে মুভি বা ফাইলের ডাইরেক্ট লিংক পাঠান।")

# --- ১. লিংক গ্রহণ ও ডাউনলোড ---
@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def leech_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    status_msg = await message.reply_text("সার্ভারে ডাউনলোড শুরু হচ্ছে... 📥")
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    try:
        download = aria2_client.add_uris([url], options={"dir": download_dir})
        while not download.is_complete:
            download.update()
            if download.has_failed:
                await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে!")
                return
            await update_progress(download.completed_length, download.total_length, "📥 সার্ভারে ডাউনলোড হচ্ছে...", status_msg)
            await asyncio.sleep(2)

        # ডাউনলোড শেষ, এখন ইউজারকে রিনেম/থাম্বনেইল এর অপশন দেওয়া
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        file_path = max(files, key=os.path.getctime)
        
        # ডাটা সেভ করে রাখা
        user_data[user_id] = {
            "file_path": file_path,
            "new_name": os.path.basename(file_path),
            "thumb": None,
            "download_dir": download_dir
        }

        await status_msg.delete()
        await message.reply_text(
            f"✅ **ডাউনলোড সম্পন্ন!**\n\n📄 **ফাইল:** `{os.path.basename(file_path)}` \n💰 **সাইজ:** {human_size(os.path.getsize(file_path))}\n\n"
            "এখন আপনি চাইলে:\n"
            "১. নতুন নাম লিখে পাঠান (রিনেম করতে)।\n"
            "২. একটি ছবি পাঠান (থাম্বনেইল সেট করতে)।\n"
            "৩. নিচের বাটনে ক্লিক করে আপলোড শুরু করুন।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="start_upload")]])
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ ভুল হয়েছে: {str(e)}")

# --- ২. রিনেম হ্যান্ডলার (টেক্সট মেসেজ) ---
@app.on_message(filters.text & filters.private)
async def rename_handler(client, message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন নাম সেট করা হয়েছে: `{message.text}`\nএখন আপলোড করতে নিচের বাটনে ক্লিক করুন।")

# --- ৩. থাম্বনেইল হ্যান্ডলার (ফটো মেসেজ) ---
@app.on_message(filters.photo & filters.private)
async def thumb_handler(client, message):
    user_id = message.from_user.id
    if user_id in user_data:
        thumb_path = f"downloads/thumb_{user_id}.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট করা হয়েছে! এখন আপলোড করতে নিচের বাটনে ক্লিক করুন।")

# --- ৪. আপলোড বাটন হ্যান্ডলার ---
@app.on_callback_query(filters.regex("start_upload"))
async def upload_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("কোনো ফাইল পাওয়া যায়নি!", show_alert=True)
        return

    data = user_data[user_id]
    file_path = data["file_path"]
    new_name = data["new_name"]
    thumb = data["thumb"]
    
    # রিনেম করা
    final_path = os.path.join(os.path.dirname(file_path), new_name)
    os.rename(file_path, final_path)
    
    status_msg = await callback_query.message.edit_text(f"📤 টেলিগ্রামে আপলোড হচ্ছে: `{new_name}`...")
    
    try:
        start_time = time.time()
        await client.send_video(
            chat_id=user_id,
            video=final_path,
            thumb=thumb,
            caption=f"✅ **ফাইল:** `{new_name}`\n💰 **সাইজ:** {human_size(os.path.getsize(final_path))}",
            supports_streaming=True,
            progress=update_progress,
            progress_args=("📤 টেলিগ্রামে আপলোড হচ্ছে...", status_msg)
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
    finally:
        if os.path.exists(data["download_dir"]): shutil.rmtree(data["download_dir"])
        if thumb and os.path.exists(thumb): os.remove(thumb)
        del user_data[user_id]

print("বট সফলভাবে রানিং হয়েছে!")
app.run()
