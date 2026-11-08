import os
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp

# .env ফাইল থেকে টোকেন লোড করা
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ভিডিও ডাউনলোড করার ফাংশন
# ভিডিও ডাউনলোড করার ফাংশন
# ভিডিও ডাউনলোড করার ফাংশন
# ভিডিও ডাউনলোড করার ফাংশন
def download_video(url):
    # লিংকটি ইউটিউবের কি না, তা চেক করা হচ্ছে
    if 'youtube.com' in url or 'youtu.be' in url:
        # কোয়ালিটি কমানোর জন্য লিমিট কমিয়ে 15MB এবং 'worst' (সবচেয়ে লো কোয়ালিটি) অপশন যোগ করা হলো
        ydl_opts = {
            'format': 'best[ext=mp4][filesize<15M]/worst[ext=mp4]/best[ext=mp4][filesize<50M]/best',
            'outtmpl': 'downloaded_video.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
    else:
        # ফেসবুক বা অন্যান্য লিংকের জন্য আপনার বর্তমানের কাজ-করা সেটিংস
        ydl_opts = {
            'format': 'best[height<=480][ext=mp4]/best[height<=360][ext=mp4]/worst',
            'outtmpl': 'downloaded_video.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_filename = ydl.prepare_filename(info_dict)
            return video_filename
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

# মেসেজ হ্যান্ডেল করার ফাংশন
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text
    # ইউটিউব, ফেসবুক বা ইন্সটাগ্রামের লিংক খোঁজার রেজেক্স (Regex)
    url_pattern = r'(https?://(?:www\.)?(?:youtube\.com|youtu\.be|facebook\.com|fb\.watch|fb\.com|instagram\.com)[^\s]+)'
    match = re.search(url_pattern, text)

    if match:
        url = match.group(1)
        
        # ১. প্রসেসিং মেসেজ পাঠানো
        processing_msg = await message.reply_text("⏳ Processing video link...")

        # ২. ভিডিও ডাউনলোড করা (আসল মেসেজ এখনই ডিলিট হবে না)
        video_path = download_video(url)

        # ৩. ভিডিও গ্রুপে পাঠানো
        if video_path and os.path.exists(video_path):
            is_sent = False
            try:
                with open(video_path, 'rb') as video_file:
                    await context.bot.send_video(
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
                await processing_msg.edit_text("❌ Failed to send video. It might be invalid.")
            finally:
                # ৪. কাজ শেষে সার্ভার বা পিসি থেকে ভিডিও ফাইল মুছে ফেলা
                if os.path.exists(video_path):
                    os.remove(video_path)
                    
            # ৫. ভিডিও ঠিকঠাক সেন্ড হলে তবেই প্রসেসিং মেসেজ এবং আসল লিংক মুছে ফেলা হবে
            if is_sent:
                await processing_msg.delete()
                try:
                    await message.delete()
                except Exception as e:
                    print(f"Could not delete original message: {e}")
        else:
            await processing_msg.edit_text("❌ Failed to download the video.")

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is not set in .env file!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    
    # সব টেক্সট মেসেজ চেক করার জন্য হ্যান্ডলার
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Reeluu Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()