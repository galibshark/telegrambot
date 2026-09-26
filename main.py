# main.py
import sqlite3
from datetime import datetime, timedelta, timezone
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from config import TELEGRAM_BOT_TOKEN, SELECTING_TAG, ENTERING_TITLE, SELECTING_DATE, ENTERING_COMMENT
import database as db
import helpers as hp
import handlers as hd

# ল্যাপটপ বা সার্ভারের টাইম ইগনোর করে ডিরেক্ট বাংলাদেশ টাইমজোন (UTC +6 ঘণ্টা)
BD_TZ = timezone(timedelta(hours=6))

# ২৪ ও ১২ ঘণ্টার রিমাইন্ডার শিডিউলার
async def double_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(BD_TZ)
    conn = sqlite3.connect("notices.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, chat_id, thread_id, tag, title, comment, due_date, weekday, reminded_24h, reminded_12h FROM notices WHERE reminded_12h = 0")
    upcoming_tasks = cursor.fetchall()
    
    for row in upcoming_tasks:
        task_id, chat_id, thread_id, tag, title, comment, due_date, weekday, r24, r12 = row
        target_dt = datetime.strptime(due_date, "%Y-%m-%d").replace(tzinfo=BD_TZ)
        diff = target_dt - now
        hours_left = diff.total_seconds() / 3600
        
        alert_msg = None
        update_col = None
        
        # ২৪ ঘণ্টা বাকি থাকতে প্রথম রিমাইন্ডার
        if 12 < hours_left <= 24 and not r24:
            alert_msg = f"🔔 **জরুরি রিমাইন্ডার (২৪ ঘণ্টা বাকি)!**\n\n"
            update_col = "reminded_24h"
            
        # ১২ ঘণ্টা বাকি থাকতে চূড়ান্ত রিমাইন্ডার
        elif 0 < hours_left <= 12 and not r12:
            alert_msg = f"🚨 **চূড়ান্ত রিমাইন্ডার (১২ ঘণ্টা বাকি)!**\n\n"
            update_col = "reminded_12h"
            
        if alert_msg:
            alert_msg += (
                f"📌 **ধরন:** {tag.capitalize()}\n"
                f"📖 **বিষয়:** {title}\n"
                f"📅 **তারিখ:** {due_date} ({weekday})\n"
                f"⏳ **সময়:** {hp.get_detailed_countdown(due_date)}\n"
            )
            if comment:
                alert_msg += f"💬 **নোট:** \"_{comment}_\"\n"
                
            alert_msg += f"\nসবাই প্রস্তুতি সম্পন্ন করে রাখুন!"
            
            try:
                kwargs = {"chat_id": chat_id, "text": alert_msg, "parse_mode": "Markdown"}
                if thread_id:
                    kwargs["message_thread_id"] = thread_id
                
                await context.bot.send_message(**kwargs)
                cursor.execute(f"UPDATE notices SET {update_col} = 1 WHERE id = ?", (task_id,))
                conn.commit()
            except Exception as e:
                print(f"Failed to send reminder for task {task_id}: {e}")
                
    conn.close()

if __name__ == "__main__":
    # ডেটাবেস ইনিশিয়ালাইজেশন
    db.init_db()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # আপনার আগের ইন্টারফেস অনুযায়ী কনভারসেশন হ্যান্ডলার
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", hd.add_start)],
        states={
            SELECTING_TAG: [CallbackQueryHandler(hd.tag_selected)],
            ENTERING_TITLE: [MessageHandler(filters.TEXT & (~filters.COMMAND), hd.title_entered)],
            SELECTING_DATE: [CallbackQueryHandler(hd.calendar_handler)],
            ENTERING_COMMENT: [MessageHandler(filters.TEXT & (~filters.COMMAND) | filters.Regex(r"^/skip$"), hd.comment_entered)],
        },
        fallbacks=[CommandHandler("cancel", hd.cancel)],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", hd.start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("exam", hd.list_exam))
    app.add_handler(CommandHandler("assignment", hd.list_assignment))
    app.add_handler(CommandHandler("presentation", hd.list_presentation))
    app.add_handler(CommandHandler("all", hd.list_all))
    app.add_handler(CommandHandler("done", hd.done_task))

    # প্রতি ১ ঘণ্টা পর পর চেক করবে (২৪ ঘণ্টা বা ১২ ঘণ্টা বাকি থাকলে মেসেজ দেবে)
    if app.job_queue:
        app.job_queue.run_repeating(double_reminder_job, interval=3600, first=10)

    print("নোটস ও ক্যালেন্ডার বট সফলভাবে চালু হয়েছে...")
    app.run_polling()