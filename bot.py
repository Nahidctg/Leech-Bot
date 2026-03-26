import os
import time
import asyncio
import subprocess
import shutil
from pyrogram import Client, filters, errors

# --- আপনার তথ্য ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("ultra_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

# ফ্লাড ওয়েট এড়াতে প্রগ্রেস আপডেট টাইমার (প্রতি ১০ সেকেন্ডে একবার)
last_edit_time = {}

async def update_progress(current, total, status_text, status_msg):
    msg_id = status_msg.id
    now = time.time()
    
    if msg_id not in last_edit_time:
        last_edit_time[msg_id] = 0
        
    if (now - last_edit_time[msg_id]) < 10:
        return

    last_edit_time[msg_id] = now
    percentage = (current * 100) / total if total > 0 else 0
    
    progress = f"**{status_text}**\n\n" \
               f"📊 সম্পন্ন: {round(percentage, 2)}%\n" \
               f"📦 সাইজ: {human_size(current)} / {human_size(total)}"
    
    try:
        await status_msg.edit_text(progress)
    except:
        pass

# অটো থাম্বনেইল জেনারেটর
async def take_screenshot(video_path, output_path):
    cmd = ["ffmpeg", "-i", video_path, "-ss", "00:00:05", "-vframes", "1", output_path, "-y"]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await process.communicate()
    return output_path if os.path.exists(output_path) else None

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("বট অনলাইন! 🚀\n\nরিনেম করতে চাইলে এভাবে পাঠান:\n`Link | NewName.mp4`\n\nঅথবা শুধু সরাসরি লিংক পাঠান।")

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def leech_handler(client, message):
    text = message.text
    if "|" in text:
        url, new_name = map(str.strip, text.split("|", 1))
    else:
        url, new_name = text.strip(), None

    status_msg = await message.reply_text("প্রসেসিং... ⏳")
    download_dir = f"downloads/{message.from_user.id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        # ১. ডাউনলোড শুরু (Aria2c)
        await status_msg.edit_text("📥 সার্ভারে ডাউনলোড হচ্ছে...")
        
        cmd = ["aria2c", "--dir", download_dir, "--max-connection-per-server=16", "-x", "16", "-s", "16", "--user-agent", user_agent, url]
        
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        
        # ডাউনলোডের সময় লাইভ প্রগ্রেস দেখা অসম্ভব aria2 কমান্ড লাইন দিয়ে সহজে, 
        # তাই আমরা ডাউনলোড শেষ হওয়া পর্যন্ত অপেক্ষা করছি। 
        await process.communicate()

        # ২. ফাইল চেক ও রিনেম
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে! লিংকটি চেক করুন।")
            return
        
        file_path = max(files, key=os.path.getctime)
        if new_name:
            final_path = os.path.join(download_dir, new_name)
            os.rename(file_path, final_path)
            file_path = final_path

        file_size = os.path.getsize(file_path)
        if file_size > 2097152000:
            await status_msg.edit_text("❌ ফাইলটি ২ জিবির চেয়ে বড়।")
            return

        # ৩. থাম্বনেইল তৈরি
        await status_msg.edit_text("🖼 ভিডিও প্রসেসিং ও থাম্বনেইল তৈরি হচ্ছে...")
        thumb_path = os.path.join(download_dir, "thumb.jpg")
        thumb = await take_screenshot(file_path, thumb_path)

        # ৪. টেলিগ্রামে ভিডিও আপলোড
        await status_msg.edit_text(f"📤 টেলিগ্রামে আপলোড হচ্ছে...\n\n📄 ফাইল: {os.path.basename(file_path)}")
        
        start_time = time.time()
        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            thumb=thumb,
            caption=f"✅ **ফাইল:** `{os.path.basename(file_path)}` \n💰 **সাইজ:** {human_size(file_size)}",
            supports_streaming=True,
            progress=update_progress,
            progress_args=("📤 টেলিগ্রামে আপলোড হচ্ছে...", status_msg)
        )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ ভুল হয়েছে: {str(e)}")
    finally:
        if os.path.exists(download_dir): shutil.rmtree(download_dir)

print("বটটি এখন পুরোপুরি রানিং!")
app.run()
