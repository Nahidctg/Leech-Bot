import os
import time
import asyncio
from pyrogram import Client, filters
import yt_dlp

# --- আপনার তথ্য দিন ---
API_ID = 1234567         # আপনার API ID
API_HASH = "your_hash"    # আপনার API Hash
BOT_TOKEN = "your_token"  # বটের টোকেন

app = Client("my_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# সাইজ দেখানোর ফাংশন
def human_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0: return f"{size:.2f} {unit}"
        size /= 1024.0

# আপলোড প্রগ্রেস বার
async def progress(current, total, status_msg, start_time):
    now = time.time()
    diff = now - start_time
    if diff < 3: return
    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff)
    
    progress_str = f"🚀 আপলোড হচ্ছে: {round(percentage, 2)}%\n" \
                   f"📦 সাইজ: {human_size(current)} / {human_size(total)}\n" \
                   f"⚡ গতি: {human_size(speed)}/s"
    try:
        await status_msg.edit_text(progress_str)
    except: pass

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def start_leech(client, message):
    url = message.text
    status_msg = await message.reply_text("লিংক প্রসেস করছি... ⏳")

    # ডাউনলোড সেটিংস (আপনার দেওয়া লিংকগুলোর জন্য পারফেক্ট)
    ydl_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    try:
        if not os.path.exists("downloads"): os.makedirs("downloads")
        
        await status_msg.edit_text("সার্ভারে ডাউনলোড হচ্ছে... 📥")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            file_name = os.path.basename(file_path)

        await status_msg.edit_text("ডাউনলোড শেষ! এখন আপনাকে পাঠাচ্ছি... 📤")
        
        start_time = time.time()
        
        # ফাইলটি সরাসরি টেলিগ্রামে পাঠানো
        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            caption=f"✅ **ফাইল:** `{file_name}`\n💰 **সাইজ:** {human_size(os.path.getsize(file_path))}",
            progress=progress,
            progress_args=(status_msg, start_time)
        )

        # কাজ শেষে ফাইল ডিলিট
        os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ ভুল হয়েছে: {str(e)}")

print("বটটি এখন কাজ করার জন্য তৈরি!")
app.run()
