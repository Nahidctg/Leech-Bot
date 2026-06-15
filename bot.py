# ==============================================================================
# --- আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন (Version 19.6 - Hybrid Gateway Upgrade) ---
# --- ফিচার: স্মার্ট ডিকোড, ৪জিবি সাপোর্ট, অ্যাডাপ্টিভ ডিসিশন মেকার, অটো-হেডার রোটেশন ---
# ==============================================================================

import os
import time
import asyncio
import subprocess
import shutil
import re
import random
import requests
import yt_dlp
import logging
from datetime import datetime
from urllib.parse import urlparse
from pyrogram import Client, filters, idle, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# লগার সেটআপ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# --- ১. গ্লোবাল কনফিগারেশন সেকশন ---
# ==============================================================================

API_ID = 28870226
API_HASH = "a5b1ff3f75941649bf5bc159782f0f00"
BOT_TOKEN = "8464633052:AAFQv6OqDkpipNyLxAE5SqgYnH9201mpK6E"

STRING_SESSION = "" 
LOG_CHANNEL = -1003999674690 

app = Client(
    "ultimate_bot_instance_v3", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    workers=100
)

user_app = None
if STRING_SESSION and len(STRING_SESSION) > 10:
    user_app = Client(
        "premium_session_account", 
        api_id=API_ID, 
        api_hash=API_HASH, 
        session_string=STRING_SESSION
    )

user_data = {}

# ==============================================================================
# --- ২. অ্যাডাপ্টিভ ডিসিশন ইউটিলিটি (AI-Like User Agent & Header Spoofer) ---
# ==============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (iPad; CPU OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
]

def get_adaptive_headers(url, original_url=None):
    """লিঙ্কের ডোমেইন অনুযায়ী স্বয়ংক্রিয় হেডার জেনারেট করে"""
    parsed = urlparse(url)
    domain = parsed.netloc
    
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    if original_url:
        headers['Referer'] = original_url
        headers['Origin'] = f"https://{urlparse(original_url).netloc}"
    else:
        headers['Referer'] = f"https://{domain}/"
    
    if "workers.dev" in domain or "mexanig" in domain:
        headers['Origin'] = f"https://{domain}"
        headers['Sec-Fetch-Dest'] = 'document'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'none'
        
    return headers

def human_size(num):
    if not num:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

def time_formatter(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def get_duration(file_path):
    try:
        metadata = extractMetadata(createParser(file_path))
        if metadata and metadata.has("duration"):
            return metadata.get("duration").seconds
    except Exception as e:
        logger.error(f"ডিউরেশন এরর: {e}")
    return 0

# ==============================================================================
# --- ৩. ইউনিফাইড প্রগ্রেস বার ---
# ==============================================================================

async def progress_bar(current, total, status_text, status_msg, start_time, last_update_time):
    now = time.time()
    if (now - last_update_time[0]) < 5:
        return
    last_update_time[0] = now

    elapsed_time = now - start_time
    speed = current / elapsed_time if elapsed_time > 0 else 0
    percentage = (current * 100) / total if total > 0 else 0
    
    remaining_bytes = total - current
    eta = remaining_bytes / speed if speed > 0 else 0
    
    bar_length = 12
    filled_length = int(percentage / (100 / bar_length))
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    
    progress_ui = (
        f"**┏━━━━━━━━━━━━━━━━━━━┓**\n"
        f"**┃ ⚡ {status_text}**\n"
        f"**┣━━━━━━━━━━━━━━━━━━━┛**\n"
        f"**┃ 🌀 [{bar}] {round(percentage, 2)}%**\n"
        f"**┃ 🚀 গতি: `{human_size(speed)}/s`**\n"
        f"**┃ 📦 সাইজ: `{human_size(current)}` / `{human_size(total)}`**\n"
        f"**┃ ⏳ বাকি সময়: `{time_formatter(eta)}`**\n"
        f"**┗━━━━━━━━━━━━━━━━━━━┛**"
    )

    try:
        await status_msg.edit_text(progress_ui)
    except errors.FloodWait as f:
        await asyncio.sleep(f.value)
    except Exception as e:
        logger.error(f"UI আপডেট এরর: {e}")

# ==============================================================================
# --- ৩.১ ডাইনামিক মিরর রোটেশন ও প্রক্সি মেকানিজম ---
# ==============================================================================

def fetch_html_with_curl(url, headers):
    """সিস্টেম লেভেলের Curl ব্যবহার করে ক্লাউডফ্লেয়ার ও TLS ব্লক বাইপাস করার চেষ্টা"""
    try:
        cmd = ["curl", "-s", "-L", "--connect-timeout", "10"]
        for key, val in headers.items():
            cmd.extend(["-H", f"{key}: {val}"])
        cmd.append(url)
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        logger.error(f"সিস্টেম Curl রান করতে ব্যর্থ: {e}")
    return None

def scrape_luluvid(url):
    """মিরর রোটেশন এবং প্রক্সি ব্যবহার করে সোর্স লিঙ্ক স্ক্র্যাপ করার প্রক্রিয়া"""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        # ইউনিক ভিডিও কোড আলাদা করা হচ্ছে
        code = path.replace('e/', '').strip('/')
        
        # Luluvid-এর সক্রিয় মিরর ডোমেনসমূহের তালিকা
        mirrors = [
            f"https://luluply.com/e/{code}",
            f"https://lulustream.co/e/{code}",
            f"https://lulusp.com/e/{code}",
            f"https://lulushare.com/e/{code}",
            f"https://lulustream.com/e/{code}",
            f"https://luluvid.com/e/{code}"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://google.com/', # জেনেরিক রিফায়ার ব্যবহারের মাধ্যমে ট্র্যাকিং ব্লক এড়ানো
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        html = None
        
        # ধাপ ১: মিররগুলোর ওপর সরাসরি সাধারণ HTTP রিকোয়েস্ট (সবচেয়ে দ্রুত মেথড)
        for m_url in mirrors:
            logger.info(f"মিরর ট্রাই করা হচ্ছে: {m_url}")
            try:
                response = requests.get(m_url, headers=headers, timeout=6)
                if response.status_code == 200 and "cloudflare" not in response.text.lower():
                    html = response.text
                    logger.info(f"মিরর {urlparse(m_url).netloc} থেকে সরাসরি সংযোগ সফল হয়েছে!")
                    break
            except Exception:
                continue
                
        # ধাপ ২: সরাসরি মেথড ব্যর্থ হলে, প্রথম ৩টি মিররে সিস্টেম Curl দিয়ে চেষ্টা
        if not html:
            for m_url in mirrors[:3]:
                logger.info(f"Curl দিয়ে মিরর ট্রাই করা হচ্ছে: {m_url}")
                html = fetch_html_with_curl(m_url, headers)
                if html and "cloudflare" not in html.lower():
                    logger.info(f"Curl দিয়ে মিরর {urlparse(m_url).netloc} সংযোগ সফল!")
                    break
                html = None
                
        # ধাপ ৩: যদি সব ব্লক থাকে, তবে প্রথম ২টি মিররের ওপর পাবলিক প্রক্সি গেটওয়ে প্রয়োগ
        if not html:
            logger.info("সকল মিরর সরাসরি ব্লকড। প্রক্সি গেটওয়ে সক্রিয় করা হচ্ছে...")
            proxy_services = [
                "https://corsproxy.io/?{}",
                "https://api.codetabs.com/v1/proxy?quest={}"
            ]
            for m_url in mirrors[:2]:
                for p_service in proxy_services:
                    p_url = p_service.format(m_url)
                    try:
                        res = requests.get(p_url, headers={'User-Agent': headers['User-Agent']}, timeout=10)
                        if res.status_code == 200 and "cloudflare" not in res.text.lower():
                            html = res.text
                            logger.info(f"প্রক্সি ও মিরর ({urlparse(m_url).netloc}) সমন্বয়ে সোর্স উদ্ধার সফল!")
                            break
                    except Exception:
                        continue
                if html:
                    break
            
        if html:
            # JSON Escaped স্ল্যাশ ক্লিন করা (যেমন: https:\/\/ -> https://)
            html = html.replace('\\/', '/')
            
            # .m3u8 বা .mp4 সোর্স ফাইল খোঁজা হচ্ছে
            stream_links = re.findall(r'["\'](https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)["\']', html)
            if stream_links:
                resolved_url = stream_links[0]
                logger.info(f"সোর্স লিঙ্ক পাওয়া গেছে: {resolved_url}")
                return resolved_url
                
            # বিকল্প রেগুলার এক্সপ্রেশন
            file_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+)["\']', html)
            if file_match:
                resolved_url = file_match.group(1)
                logger.info(f"বিকল্প সোর্স লিঙ্ক পাওয়া গেছে: {resolved_url}")
                return resolved_url
                
    except Exception as e:
        logger.error(f"Luluvid মিরর রোটেশন স্ক্র্যাপিংয়ে ত্রুটি: {e}")
    return None

# ==============================================================================
# --- ৪. লিঙ্ক রেজলভার ENGINE ---
# ==============================================================================

def get_smart_link(url):
    """ইঞ্জিনটি স্বয়ংক্রিয়ভাবে পরীক্ষা করবে লিঙ্কটি সরাসরি নাকি কোনো স্ক্র্যাপার প্রয়োজন"""
    logger.info(f"অ্যাডাপ্টিভ এনালাইসিস শুরু: {url}")
    
    # ১. Luluvid/Lulustream ডোমেন সনাক্তকরণ
    if any(domain in url.lower() for domain in ["luluvid.com", "lulustream.com", "lulushare.com", "luluply.com", "lulustream.co"]):
        scraped_link = scrape_luluvid(url)
        if scraped_link:
            return scraped_link
        else:
            # যদি সব বাইপাস মেথড ব্যর্থ হয়, তবে বিশেষ ফ্ল্যাগ রিটার্ন করা হবে
            logger.error("Luluvid এর সব বাইপাস মিরর মেথড ব্যর্থ হয়েছে।")
            return "LULU_FAILED"

    headers = get_adaptive_headers(url)
    
    try:
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.head(url, allow_redirects=True, timeout=10)
        final_url = response.url
        
        if any(ext in final_url.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.ts']):
            logger.info(f"সরাসরি ভিডিও লিঙ্ক পাওয়া গেছে: {final_url}")
            return final_url
            
        url = final_url
    except Exception as e:
        logger.warning(f"প্রাথমিক হেড চেকিং ব্যর্থ: {e}")

    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'format': 'best',
        'noplaylist': True, 
        'nocheckcertificate': True,
        'extractor_args': {'generic': ['impersonate']},
        'http_headers': headers
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            resolved_url = info.get('url', url)
            logger.info(f"yt-dlp দ্বারা রেজলভড লিঙ্ক: {resolved_url}")
            return resolved_url
        except Exception:
            return url

# ==============================================================================
# --- ৫. মেসেজ হ্যান্ডলারসমূহ ---
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    mode = "Premium (4GB Support) ✅" if user_app else "Normal (2GB Limited) ⚠️"
    
    welcome_text = (
        f"**বট অনলাইন! 🚀 (Version 19.6 - Hybrid Gateway Upgrade)**\n\n"
        f"এই সংস্করণে যুক্ত করা হয়েছে হাইব্রিড ফাস্ট-আপলোড গেটওয়ে, মিরর ডোমেইন রোটেশন প্রযুক্তি এবং দীর্ঘ ফাইলের নামজনিত ক্র্যাশ সমাধান (Errno 36)।\n\n"
        f"**বর্তমান মোড:** `{mode}`\n"
        f"যেকোনো ভিডিও লিঙ্ক পাঠান।"
    )
    await message.reply_text(welcome_text)

# ==============================================================================
# --- ৬. ডাউনলোড সেকশন (Decision Maker with Hybrid Fast-Path) ---
# ==============================================================================

@app.on_message(filters.regex(r'https?://[^\s]+') & filters.private)
async def download_handler(client, message):
    url = message.text.strip()
    user_id = message.from_user.id
    loop = asyncio.get_event_loop()
    
    if user_id in user_data:
        shutil.rmtree(user_data[user_id]["dir"], ignore_errors=True)
        del user_data[user_id]
        
    status_msg = await message.reply_text("🔎 লিঙ্ক বিশ্লেষণ ও সেরা ডাউনলোড মেথড খোঁজা হচ্ছে...")
    
    direct_link = await asyncio.to_thread(get_smart_link, url)
    
    # Luluvid সম্পূর্ণ ব্লকড হলে ব্যবহারকারীকে স্পষ্ট নোটিফিকেশন পাঠানো হবে
    if direct_link == "LULU_FAILED":
        shutil.rmtree(f"downloads/{user_id}_*", ignore_errors=True)
        await status_msg.edit_text(
            "❌ **ডাউনলোড ব্যর্থ!**\n\n"
            "**কারণ:** সোর্স সার্ভার সংযোগ প্রত্যাখ্যান করেছে। Luluvid সাইটটি বর্তমানে তাদের সব মিরর ডোমেইনসহ আপনার হোস্টিং আইপি এবং আমাদের প্রক্সি গেটওয়েগুলো সাময়িকভাবে ব্লক করে দিয়েছে (Cloudflare Captcha Lock)।\n"
            "অনুগ্রহ করে অন্য কোনো সাইটের লিঙ্ক ব্যবহার করুন অথবা কিছু সময় পর আবার ট্রাই করুন।"
        )
        return
        
    if not direct_link:
        direct_link = url
        
    parsed_link = urlparse(direct_link)
    
    # ----------------------------------------------------------------------------------
    # ⚡ নতুন ফিচার: ছোট ও সরাসরি লিঙ্কের জন্য হাইব্রিড ফাস্ট-আপলোড গেটওয়ে শর্টকাট
    # ----------------------------------------------------------------------------------
    is_fast_eligible = any(parsed_link.path.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.mov'])
    
    if is_fast_eligible:
        try:
            headers = get_adaptive_headers(direct_link, original_url=url)
            # HEAD রিকোয়েস্ট পাঠিয়ে ফাইল সাইজ জেনে নেওয়া হচ্ছে
            head_res = requests.head(direct_link, headers=headers, allow_redirects=True, timeout=5)
            file_size = int(head_res.headers.get('content-length', 0))
            
            # যদি সরাসরি ভিডিও ফাইলটি ২০ মেগাবাইটের কম হয়, তবে ফাস্ট-গেটওয়ে দিয়ে সরাসরি আপলোড দেওয়া হবে
            if 0 < file_size <= 20 * 1024 * 1024:
                await status_msg.edit_text("⚡ ফাস্ট-আপলোড গেটওয়ে সক্রিয় করা হচ্ছে...")
                filename = os.path.basename(parsed_link.path) or "video.mp4"
                
                await client.send_video(
                    chat_id=user_id, 
                    video=direct_link, 
                    caption=f"✅ **ফাস্ট আপলোড সম্পন্ন!**\n\n📄 **ফাইল:** `{filename}`\n💰 **সাইজ:** `{human_size(file_size)}`"
                )
                await status_msg.delete()
                return # সফল হলে এখানেই প্রসেস শেষ, লোকাল ডাউনলোডের প্রসেসিং বাইপাস করা হলো।
        except Exception as fast_err:
            logger.warning(f"ফাস্ট-আপলোড গেটওয়ে ব্যর্থ হয়েছে: {fast_err}। সাধারণ ডাউনলোড লাইনে রি-ডাইরেক্ট করা হচ্ছে...")
    # ----------------------------------------------------------------------------------
    
    headers = get_adaptive_headers(direct_link, original_url=url)
    
    download_dir = f"downloads/{user_id}_{int(time.time())}"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    start_time = time.time()
    last_update_time = [0]

    # সিদ্ধান্ত গ্রহণ: HLS (.m3u8) সরাসরি স্ট্রিম মেথড বাইপাস করে মেথড-১ (YT-DLP) এ পাঠানো হবে
    is_direct_file = (any(ext in direct_link.lower() for ext in ['.mkv', '.mp4', '.zip', '.rar', '.mov', '.avi', '.ts']) 
                      or "workers.dev" in direct_link) and ".m3u8" not in direct_link.lower()
    
    if not is_direct_file:
        # মেথড ১: YT-DLP ব্যবহার করা হচ্ছে
        await status_msg.edit_text("📥 ডাউনলোড ইঞ্জিন সক্রিয় করা হচ্ছে (YT-DLP)...")
        try:
            def ydl_progress_hook(d):
                if d['status'] == 'downloading':
                    current = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                    asyncio.run_coroutine_threadsafe(
                        progress_bar(current, total, "ডাউনলোড হচ্ছে...", status_msg, start_time, last_update_time),
                        loop
                    )

            # trim_file_name এবং %(title).80s ব্যবহারের মাধ্যমে Errno 36 (File name too long) সমাধান করা হয়েছে
            ydl_opts = {
                'outtmpl': f'{download_dir}/%(title).80s.%(ext)s',
                'trim_file_name': 80,
                'progress_hooks': [ydl_progress_hook],
                'nocheckcertificate': True, 
                'quiet': True,
                'no_warnings': True,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'concurrent_fragment_downloads': 3,
                'buffersize': 1024 * 64,
                'http_headers': headers
            }
            
            await asyncio.to_thread(yt_dlp.YoutubeDL(ydl_opts).download, [direct_link])
            
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if not f.endswith(".aria2")]
            if files:
                file_path = max(files, key=os.path.getctime)
                await finish_download(user_id, file_path, download_dir, status_msg, message)
                return
        except Exception as e:
            logger.error(f"YT-DLP ইঞ্জিন ব্যর্থ হয়েছে: {e}")
            if ".m3u8" in direct_link.lower() or "lulucdn" in direct_link.lower():
                shutil.rmtree(download_dir, ignore_errors=True)
                await status_msg.edit_text(
                    f"❌ **ডাউনলোড ব্যর্থ!**\n\n"
                    f"**কারণ:** সোর্স সার্ভার সংযোগ প্রত্যাখ্যান করেছে বা সিডিএন আইপি ব্লক করা হয়েছে।\n"
                    f"`{str(e)[:150]}`"
                )
                return

    # মেথড ২: সাধারণ ভিডিও এবং ক্লাউডফ্লেয়ার ওয়ার্কার বাইপাস ইঞ্জিন (HTTP-Stream chunking)
    await status_msg.edit_text("⚙️ প্রক্সি বাইপাস ইঞ্জিন সক্রিয় হচ্ছে (HTTP-Stream)...")
    try:
        parsed_url = urlparse(direct_link)
        filename = os.path.basename(parsed_url.path) or "video_file.mp4"
        if not any(filename.lower().endswith(ext) for ext in ['.mp4', '.mkv', '.mov', '.avi', '.zip', '.rar', '.ts']):
            filename += ".mp4"
            
        # অতিরিক্ত দীর্ঘ নাম এড়াতে ফাইলের নামের দৈর্ঘ্য লিমিট করা হচ্ছে
        if len(filename) > 80:
            name, ext = os.path.splitext(filename)
            filename = name[:70] + ext

        file_path = os.path.join(download_dir, filename)
        
        response = requests.get(direct_link, headers=headers, stream=True, timeout=45)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        content_type = response.headers.get('content-type', '')
        if "text/html" in content_type and total_size < 100 * 1024:
            raise ValueError("সার্ভার রিকোয়েস্ট রিজেক্ট করেছে (আইপি বা সিকিউরিটি লক)")

        downloaded = 0
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        await progress_bar(downloaded, total_size, "সেশন বাইপাস ডাউনলোড...", status_msg, start_time, last_update_time)
                        
        await finish_download(user_id, file_path, download_dir, status_msg, message)
        
    except Exception as e:
        logger.error(f"সবগুলো মেথড ব্যর্থ হয়েছে: {e}")
        shutil.rmtree(download_dir, ignore_errors=True)
        await status_msg.edit_text(f"❌ **ডাউনলোড ব্যর্থ!**\n\n**কারণ:** সার্ভারটি রিকোয়েস্ট ব্লক করেছে অথবা আইপি লক রয়েছে।\n`{str(e)}`")

# ==============================================================================
# --- ৬.১ ডাউনলোড শেষ করার কমন মডিউল ---
# ==============================================================================

async def finish_download(user_id, file_path, download_dir, status_msg, message):
    file_size = os.path.getsize(file_path)
    user_data[user_id] = {
        "file_path": file_path, 
        "new_name": os.path.basename(file_path),
        "thumb": None, 
        "dir": download_dir
    }
    try:
        await status_msg.delete()
    except Exception:
        pass
        
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("📤 আপলোড শুরু করুন", callback_data="upload")]])
    await message.reply_text(
        f"✅ **ডাউনলোড সম্পন্ন!**\n\n"
        f"📄 **ফাইল:** `{os.path.basename(file_path)}` \n"
        f"💰 **সাইজ:** `{human_size(file_size)}` \n\n"
        f"নাম বা থাম্বনেইল পাঠিয়ে ফাইলটি কাস্টমাইজ করতে পারেন অথবা আপলোড দিন।",
        reply_markup=markup
    )

# ==============================================================================
# --- ७. রিনেম ও থাম্বনেইল হ্যান্ডলার ---
# ==============================================================================

@app.on_message(filters.private & (filters.text | filters.photo) & ~filters.command(["start"]))
async def customization_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_data:
        return

    if message.text:
        user_data[user_id]["new_name"] = message.text.strip()
        await message.reply_text(f"📝 নতুন নাম সেট হয়েছে: `{message.text}`")
    
    elif message.photo:
        thumb_path = f"{user_data[user_id]['dir']}/thumb.jpg"
        await message.download(file_name=thumb_path)
        user_data[user_id]["thumb"] = thumb_path
        await message.reply_text("🖼 থাম্বনেইল সেট করা হয়েছে!")

# ==============================================================================
# --- ৮. আপলোড সেকশন ---
# ==============================================================================

@app.on_callback_query(filters.regex("upload"))
async def upload_callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id not in user_data:
        await callback_query.answer("ডেটা পাওয়া যায়নি! নতুন করে লিঙ্ক পাঠান।", show_alert=True)
        return
    
    data = user_data[user_id]
    old_path = data["file_path"]
    
    ext = os.path.splitext(old_path)[1]
    final_name = data["new_name"] if data["new_name"].endswith(ext) else data["new_name"] + ext
    new_path = os.path.join(os.path.dirname(old_path), final_name)
    os.rename(old_path, new_path)
    
    status_msg = await callback_query.message.edit_text("📤 আপলোড প্রস্তুতি চলছে...")
    start_time = time.time()
    last_update_time = [0]

    async def upload_progress(current, total):
        await progress_bar(current, total, "আপলোড হচ্ছে...", status_msg, start_time, last_update_time)

    try:
        file_size = os.path.getsize(new_path)
        duration = get_duration(new_path)

        if user_app and LOG_CHANNEL:
            await status_msg.edit_text("📤 ৪জিবি প্রিমিয়াম গেটওয়ে দিয়ে আপলোড হচ্ছে...")
            
            sent_msg = await user_app.send_video(
                chat_id=LOG_CHANNEL, 
                video=new_path, 
                duration=duration,
                thumb=data["thumb"], 
                caption=f"✅ `{final_name}`", 
                progress=upload_progress
            )
            
            await app.copy_message(
                chat_id=user_id, 
                from_chat_id=LOG_CHANNEL, 
                message_id=sent_msg.id,
                caption=f"✅ **ফাইল:** `{final_name}`\n💰 **সাইজ:** `{human_size(file_size)}`"
            )
        else:
            if file_size > 2000*1024*1024:
                await status_msg.edit_text("❌ ২জিবির বড় ফাইল। সেশন ছাড়া আপলোড সম্ভব নয়।")
                return
                
            await app.send_video(
                chat_id=user_id, 
                video=new_path, 
                duration=duration, 
                thumb=data["thumb"], 
                caption=f"✅ `{final_name}`", 
                progress=upload_progress
            )
            
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"আপলোড এরর: {e}")
        await status_msg.edit_text(f"❌ আপলোড এরর: {str(e)}")
        
    finally:
        if os.path.exists(data["dir"]):
            shutil.rmtree(data["dir"], ignore_errors=True)
        if user_id in user_data:
            del user_data[user_id]

# ==============================================================================
# --- ৯. সিস্টেম রানার সেকশন ---
# ==============================================================================

async def start_all_services():
    print("-" * 50)
    print("আলটিমেট টেলিগ্রাম ভিডিও প্রসেসিং ইঞ্জিন স্টার্ট হচ্ছে... (Version 19.6)")
    
    await app.start()
    bot_info = await app.get_me()
    print(f"বট ক্লায়েন্ট স্টার্ট হয়েছে: @{bot_info.username} ✅")
    
    if user_app:
        try:
            await user_app.start()
            premium_info = await user_app.get_me()
            print(f"প্রিমিয়াম ইউজার সেশন অনলাইন: {premium_info.first_name} ✅")
        except Exception as e:
            print(f"⚠️ প্রিমিয়াম সেশন এরর: {e}")
    
    print("সার্ভার এখন পুরোপুরি অনলাইন! 🚀")
    print("-" * 50)
    
    await idle()
    
    await app.stop()
    if user_app:
        await user_app.stop()

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(start_all_services())
    except KeyboardInterrupt:
        print("\nবট শাটডাউন করা হয়েছে।")
