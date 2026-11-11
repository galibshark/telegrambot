import os
import re
import asyncio
from dotenv import load_dotenv
from telegram import Bot
import yt_dlp

# .env ফাইল থেকে টোকেন লোড করা
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ভিডিও ডাউনলোড করার ফাংশন
def download_video(url):
    if 'youtube.com' in url or 'youtu.be' in url:
        ydl_opts = {
            'format': 'best[ext=mp4][filesize<15M]/worst[ext=mp4]/best[ext=mp4][filesize<50M]/best',
            'outtmpl': 'downloaded_video.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
    else:
        ydl_opts = {
            'format': 'best[height<=480][ext=mp4]/best[height<=360][ext=mp4]/worst',
            'outtmpl': 'downloaded_video.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info_dict)
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

# মেইন ফাংশন - যা শুধু একবার রান হবে এবং কাজ শেষে বন্ধ হয়ে যাবে
async def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set in .env file!")
        return

    bot = Bot(token=BOT_TOKEN)
    print("Checking for new links...")
    
    try:
        # নতুন মেসেজ আছে কি না চেক করা
        updates = await bot.get_updates(timeout=2)
    except Exception as e:
        print(f"Failed to get updates: {e}")
        return

    if not updates:
        print("No new messages found. Going back to sleep! 😴")
        return

    for update in updates:
        message = update.message
        if message and message.text:
            text = message.text
            url_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|facebook\.com|fb\.watch|fb\.com|instagram\.com)[^\s]+)'
            match = re.search(url_pattern, text)

            if match:
                url = match.group(1)
                processing_msg = await message.reply_text("⏳ Processing video link...")

                video_path = download_video(url)

                if video_path and os.path.exists(video_path):
                    is_sent = False
                    try:
                        with open(video_path, 'rb') as video_file:
                            await bot.send_video(
                                chat_id=message.chat_id,
                                video=video_file,
                                caption=f"<a href='{url}'>🔗 Link</a>",
                                parse_mode='HTML',
                                read_timeout=120,
                                write_timeout=120
                            )
                            is_sent = True
                    except Exception as e:
                        print(f"Could not send video: {e}")
                        await processing_msg.edit_text("❌ Failed to send video.")
                    finally:
                        if os.path.exists(video_path):
                            os.remove(video_path)
                            
                    if is_sent:
                        await processing_msg.delete()
                        try:
                            await message.delete()
                        except:
                            pass
                else:
                    await processing_msg.edit_text("❌ Failed to download.")
        
        # সবশেষে টেলিগ্রামকে জানিয়ে দেওয়া যে এই মেসেজটি পড়া শেষ!
        await bot.get_updates(offset=update.update_id + 1)
        print("✅ Task Completed! Closing script to save RAM.")

if __name__ == "__main__":
    asyncio.run(main())
