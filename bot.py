import os
import time
import asyncio
import subprocess
from pyrogram import Client, filters

# --- আপনার তথ্য বসানো হয়েছে ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("leech_direct_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def get_human_size(num):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

async def progress_for_pyrogram(current, total, ud_type, message, start_time):
    now = time.time()
    diff = now - start_time
    if diff < 3: return
    percentage = current * 100 / total
    speed = current / diff
    
    status = f"**{ud_type}**\n"
    status += f"📊 প্রগ্রেস: {round(percentage, 2)}%\n"
    status += f"🚀 গতি: {get_human_size(speed)}/s"
    
    try:
        await message.edit_text(status)
    except: pass

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def leech_handler(client, message):
    url = message.text
    sent_msg = await message.reply_text("লিংকটি এনালাইজ করছি... 🔎")

    # ব্রাউজার হেডার যাতে Cloudflare মনে করে আপনি আসল ইউজার
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    try:
        await sent_msg.edit_text("সার্ভারে ডাউনলোড হচ্ছে (Aria2)... 📥")
        
        # ফাইলটি যেখানে সেভ হবে সেই ফোল্ডার
        download_dir = "downloads"
        if not os.path.exists(download_dir): os.makedirs(download_dir)

        # Aria2 কমান্ড যা রিডাইরেক্ট এবং ক্লাউডফ্লেয়ার হ্যান্ডেল করবে
        # -x 16 মানে ১৬টি কানেকশন ব্যবহার করবে (দ্রুত হবে)
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--console-log-level=error",
            "-x", "16", 
            "-s", "16", 
            "--user-agent", user_agent,
            "--follow-torrent=mem",
            "--content-disposition-default-utf8=true",
            url
        ]

        # ডাউনলোড শুরু
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # ডাউনলোড করা ফাইলটি খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        if not files:
            await sent_msg.edit_text("❌ ভুল হয়েছে: ফাইলটি ডাউনলোড করা যায়নি। লিংকটি প্রোটেক্টেড বা ইনভ্যালিড।")
            return
        
        # সবচেয়ে নতুন ফাইলটি সিলেক্ট করা
        file_path = max(files, key=os.path.getctime)
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        await sent_msg.edit_text(f"ডাউনলোড শেষ! সাইজ: {get_human_size(file_size)}\nএখন টেলিগ্রামে আপলোড হচ্ছে... 📤")

        # টেলিগ্রামে পাঠানো
        start_time = time.time()
        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            caption=f"✅ **ফাইল:** `{file_name}`\n💰 **সাইজ:** {get_human_size(file_size)}",
            progress=progress_for_pyrogram,
            progress_args=("টেলিগ্রামে পাঠানো হচ্ছে...", sent_msg, start_time)
        )

        # কাজ শেষে ফাইল ডিলিট
        os.remove(file_path)
        await sent_msg.delete()

    except Exception as e:
        await sent_msg.edit_text(f"❌ এরর: {str(e)}")

print("বটটি এখন কাজ করার জন্য তৈরি!")
app.run()
