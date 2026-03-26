import os
import time
import asyncio
from pyrogram import Client, filters, errors

# --- কনফিগারেশন (আপনার দেওয়া তথ্য) ---
API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAHi2fyYM0GibUBMbJaM-5HsojLqdNNlOqo"

app = Client("final_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফাইল সাইজ ফরম্যাট করার জন্য
def human_size(num):
    if not num: return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0: return f"{num:.2f} {unit}"
        num /= 1024.0

# আপলোড প্রগ্রেস ট্র্যাকার (Flood Wait এড়াতে)
progress_info = {}

async def progress_func(current, total, status_msg, start_time):
    msg_id = status_msg.id
    now = time.time()
    
    # প্রতি ৮ সেকেন্ড পর পর প্রগ্রেস আপডেট হবে (টেলিগ্রাম ব্লক রোধ করতে)
    last_update = progress_info.get(msg_id, 0)
    if (now - last_update) < 8:
        return
        
    progress_info[msg_id] = now
    percentage = current * 100 / total
    speed = current / (now - start_time + 1)
    
    status_text = (
        f"📤 **টেলিগ্রামে আপলোড হচ্ছে...**\n\n"
        f"📊 সম্পন্ন: {round(percentage, 2)}%\n"
        f"🚀 গতি: {human_size(speed)}/s\n"
        f"📦 সাইজ: {human_size(current)} / {human_size(total)}"
    )
    
    try:
        await status_msg.edit_text(status_text)
    except errors.FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception:
        pass

# --- স্টার্ট কমান্ড ---
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text(
        f"হ্যালো {message.from_user.first_name}!\n\n"
        "আমি একটি **Direct Link Downloader** বট।\n"
        "আমাকে যেকোনো মুভি বা ফাইল ডাউনলোড লিংক পাঠান, আমি সেটি সরাসরি আপনাকে পাঠিয়ে দেব।\n\n"
        "⚡ **বট স্ট্যাটাস:** অনলাইন"
    )

# --- ডিরেক্ট লিংক ডাউনলোড ও আপলোড লজিক ---
@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def leech_handler(client, message):
    url = message.text
    status_msg = await message.reply_text("লিংক প্রসেস করছি... ⏳")
    
    download_dir = f"downloads/{message.from_user.id}_{int(time.time())}"
    if not os.path.exists(download_dir): os.makedirs(download_dir)

    # ব্রাউজার ইউজার এজেন্ট (Cloudflare এর জন্য)
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

    try:
        await status_msg.edit_text("সার্ভারে ডাউনলোড হচ্ছে... 📥")
        
        # Aria2 কমান্ড (সবচেয়ে শক্তিশালী সেটিংস)
        cmd = [
            "aria2c", 
            "--dir", download_dir,
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--user-agent", user_agent,
            "--follow-torrent=mem",
            "--content-disposition-default-utf8=true",
            url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # ডাউনলোড করা ফাইলটি খুঁজে বের করা
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]
        if not files:
            await status_msg.edit_text("❌ ডাউনলোড ব্যর্থ! লিংকটি কাজ করছে না অথবা সার্ভার থেকে ব্লক করা হয়েছে।")
            return
        
        file_path = max(files, key=os.path.getctime)
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # টেলিগ্রাম বট লিমিট চেক (২ জিবি)
        if file_size > 2097152000:
            await status_msg.edit_text(f"❌ এরর: ফাইলটি ২ জিবির বড় ({human_size(file_size)})। বট এটি পাঠাতে পারবে না।")
            return

        await status_msg.edit_text(f"ডাউনলোড শেষ! সাইজ: {human_size(file_size)}\nএখন টেলিগ্রামে আপলোড হচ্ছে... 📤")

        # আপলোড শুরু
        start_time = time.time()
        await client.send_document(
            chat_id=message.chat.id,
            document=file_path,
            caption=f"✅ **ফাইল:** `{file_name}`\n💰 **সাইজ:** {human_size(file_size)}",
            progress=progress_func,
            progress_args=(status_msg, start_time)
        )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ ভুল হয়েছে: {str(e)}")
    
    finally:
        # ডাউনলোড ফোল্ডার ক্লিন করা
        if os.path.exists(download_dir):
            import shutil
            shutil.rmtree(download_dir)

print("বটটি এখন পুরোপুরি রানিং!")
app.run()
