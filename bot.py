import os
import time
import asyncio
import shutil
from pyrogram import Client, filters, errors
import aria2p

# --- কনফিগারেশন ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("ultimate_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Aria2p ক্লায়েন্ট সেটআপ
aria2 = aria2p.API(aria2p.Client(host="http://localhost", port=6800, secret=""))

# ফাইল সাইজ ফরম্যাট
def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

# প্রগ্রেস বার আপডেট করার ফাংশন
async def update_progress(current, total, status_text, status_msg, last_update_time):
    now = time.time()
    if (now - last_update_time[0]) < 8: return
    last_update_time[0] = now
    
    percentage = current * 100 / total
    progress = f"{status_text}\n📊 সম্পন্ন: {round(percentage, 2)}%\n📦 {human_size(current)} / {human_size(total)}"
    try:
        await status_msg.edit_text(progress)
    except: pass

# --- অটো থাম্বনেইল জেনারেটর ---
async def take_screenshot(video_path, output_path):
    cmd = f"ffmpeg -i '{video_path}' -ss 00:00:05 -vframes 1 '{output_path}'"
    process = await asyncio.create_subprocess_shell(cmd)
    await process.communicate()
    return output_path if os.path.exists(output_path) else None

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("বট অনলাইন! রিনেম করতে চাইলে এভাবে পাঠান:\n`Link | NewName.mp4`\nঅথবা শুধু লিংক পাঠান।")

# --- মেইন লিচ হ্যান্ডলার ---
@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def leech_handler(client, message):
    text = message.text
    if "|" in text:
        url, new_name = text.split("|")
        url = url.strip()
        new_name = new_name.strip()
    else:
        url = text.strip()
        new_name = None

    status_msg = await message.reply_text("প্রসেসিং... ⏳")
    download_dir = f"downloads/{message.from_user.id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    try:
        # ১. সার্ভারে ডাউনলোড (Aria2p প্রগ্রেস সহ)
        download = aria2.add_uris([url], options={"dir": download_dir})
        last_update = [0]
        
        while not download.is_complete:
            download.update()
            if download.has_failed:
                await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ হয়েছে!")
                return
            await update_progress(download.completed_length, download.total_length, "📥 সার্ভারে ডাউনলোড হচ্ছে...", status_msg, last_update)
            await asyncio.sleep(2)

        # ২. ফাইল রিনেম এবং পাথ ঠিক করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        file_path = max(files, key=os.path.getctime)
        
        if new_name:
            final_path = os.path.join(download_dir, new_name)
            os.rename(file_path, final_path)
            file_path = final_path

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # ৩. থাম্বনেইল তৈরি
        await status_msg.edit_text("🖼 থাম্বনেইল তৈরি হচ্ছে...")
        thumb_path = os.path.join(download_dir, "thumb.jpg")
        thumb = await take_screenshot(file_path, thumb_path)

        # ৪. টেলিগ্রামে ভিডিও হিসেবে আপলোড
        await status_msg.edit_text(f"📤 আপলোড হচ্ছে: {file_name}")
        last_update = [0]
        
        start_time = time.time()
        await client.send_video(
            chat_id=message.chat.id,
            video=file_path,
            thumb=thumb,
            duration=0, # অটো ডিটেক্ট করবে
            caption=f"✅ **File:** `{file_name}`\n💰 **Size:** {human_size(file_size)}",
            supports_streaming=True,
            progress=update_progress,
            progress_args=("📤 টেলিগ্রামে আপলোড হচ্ছে...", status_msg, last_update)
        )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ ভুল হয়েছে: {str(e)}")
    finally:
        if os.path.exists(download_dir): shutil.rmtree(download_dir)

# Aria2 Daemon স্টার্ট করা এবং বট রান করা
if __name__ == "__main__":
    # Aria2 RPC চালু না থাকলে চালু করবে
    subprocess.Popen(["aria2c", "--enable-rpc", "--rpc-listen-all=false", "--rpc-listen-port=6800", "--daemon=true"])
    print("বট এবং Aria2 RPC রানিং...")
    app.run()
