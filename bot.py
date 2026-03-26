import os
import time
import asyncio
import subprocess
from pyrogram import Client, filters

# --- আপনার তথ্য ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("pro_direct_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

async def progress_func(current, total, status_msg, start_time):
    now = time.time()
    if (now - start_time) < 4: return
    percentage = current * 100 / total
    speed = current / (now - start_time + 1)
    try:
        await status_msg.edit_text(f"📤 আপলোড হচ্ছে: {round(percentage, 2)}%\n🚀 গতি: {human_size(speed)}/s")
    except: pass

@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply_text("বটটি এখন রানিং! আপনার ডাইরেক্ট ডাউনলোড লিংকটি পাঠান।")

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def leech_handler(client, message):
    url = message.text
    status_msg = await message.reply_text("প্রসেসিং... ⏳")
    
    # ডাউনলোড ডিরেক্টরি তৈরি
    download_dir = "downloads"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    # ব্রাউজার হেডার
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        await status_msg.edit_text("সার্ভারে ডাউনলোড শুরু হয়েছে... 📥")
        
        # Aria2 কমান্ড
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "-x", "16", 
            "-s", "16", 
            "--user-agent", user_agent,
            "--content-disposition-default-utf8=true",
            url
        ]

        # ডাউনলোড রান করা এবং এরর চেক করা
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        # ফাইলটি চেক করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        if not files:
            error_details = stderr.decode() if stderr else "No files found."
            await status_msg.edit_text(f"❌ ডাউনলোড ব্যর্থ!\nসার্ভার এরর: `{error_details[:200]}`")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # ২ জিবি লিমিট চেক
        if file_size > 2097152000: # 2GB limit
            await status_msg.edit_text(f"❌ এরর: ফাইলটি ২ জিবির বেশি ({human_size(file_size)})। এটি পাঠানো সম্ভব নয়।")
            os.remove(file_path)
            return

        await status_msg.edit_text(f"ডাউনলোড শেষ! সাইজ: {human_size(file_size)}\nএখন টেলিগ্রামে পাঠানো হচ্ছে... 📤")

        start_time = time.time()
        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            caption=f"✅ **ফাইল:** `{file_name}`\n💰 **সাইজ:** {human_size(file_size)}",
            progress=progress_func,
            progress_args=(status_msg, start_time)
        )

        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ মেইন এরর: {str(e)}")

print("বটটি সফলভাবে রানিং হয়েছে!")
app.run()
