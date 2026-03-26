import os
import time
import asyncio
from pyrogram import Client, filters

# --- আপনার তথ্যগুলো এখানে আপডেট করা হয়েছে ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("my_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফাইল সাইজ সুন্দরভাবে দেখানোর ফাংশন
def human_size(size):
    if not size: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0: return f"{size:.2f} {unit}"
        size /= 1024.0

# আপলোড প্রগ্রেস বার
async def progress(current, total, status_msg, start_time):
    now = time.time()
    diff = now - start_time
    if diff < 3: return # প্রতি ৩ সেকেন্ড পরপর আপডেট হবে
    
    percentage = current * 100 / total
    speed = current / diff
    
    progress_str = f"📤 টেলিগ্রামে পাঠানো হচ্ছে...\n" \
                   f"📊 প্রগ্রেস: {round(percentage, 2)}%\n" \
                   f"🚀 গতি: {human_size(speed)}/s"
    try:
        await status_msg.edit_text(progress_str)
    except: pass

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def start_leech(client, message):
    url = message.text
    status_msg = await message.reply_text("লিংক প্রসেস করছি... ⏳")

    # ব্রাউজার ইউজার এজেন্ট (Cloudflare এরর এড়াতে)
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    try:
        await status_msg.edit_text("সার্ভারে ডাউনলোড হচ্ছে... 📥")
        
        # Aria2 কমান্ড যা রিডাইরেক্ট লিংক সাপোর্ট করে
        cmd = [
            "aria2c", 
            "--console-log-level=error",
            "-x", "16", 
            "-s", "16", 
            "--user-agent", user_agent,
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
        all_files = [f for f in os.listdir('.') if os.path.isfile(f) and f not in ['bot.py', 'requirements.txt', 'Procfile', '.gitignore']]
        if not all_files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে! লিংকটি কাজ করছে না।")
            return
        
        file_path = all_files[0] 
        file_size = os.path.getsize(file_path)

        await status_msg.edit_text("ডাউনলোড শেষ! এখন টেলিগ্রামে আপলোড হচ্ছে... 📤")
        
        start_time = time.time()
        
        # সরাসরি টেলিগ্রামে ফাইল পাঠানো
        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            caption=f"✅ **ফাইল:** `{file_path}`\n💰 **সাইজ:** {human_size(file_size)}",
            progress=progress,
            progress_args=(status_msg, start_time)
        )

        # কাজ শেষে সার্ভার থেকে ফাইল ডিলিট
        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ ভুল হয়েছে: {str(e)}")

print("বটটি এখন কাজ করার জন্য তৈরি!")
app.run()
