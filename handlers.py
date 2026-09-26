# handlers.py
import sqlite3
import asyncio
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import helpers as hp
from config import SELECTING_TAG, ENTERING_TITLE, SELECTING_DATE, ENTERING_COMMENT

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg_id = update.message.message_id
    thread_id = update.message.message_thread_id if update.message else None
    
    bot_msg = await update.message.reply_text(
        "👋 হ্যালো! আমি আপনার স্টাডি নোটিস বট।\nনতুন নোটিস যোগ করতে `/add` কমান্ড দিন।", 
        parse_mode="Markdown",
        message_thread_id=thread_id
    )
    await asyncio.sleep(5)
    await hp.clean_temp_messages(chat_id, [user_msg_id, bot_msg.message_id], context.bot)

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["temp_msgs"] = [update.message.message_id]
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Exam", callback_data="exam"),
            InlineKeyboardButton("📚 Assignment", callback_data="assignment"),
        ],
        [
            InlineKeyboardButton("📊 Presentation", callback_data="presentation"),
            InlineKeyboardButton("📌 Other", callback_data="other"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    thread_id = update.message.message_thread_id if update.message else None
    
    bot_msg = await update.message.reply_text(
        "কোন ধরনের নোটিস যোগ করতে চান? অপশন বেছে নিন:",
        reply_markup=reply_markup,
        message_thread_id=thread_id
    )
    context.user_data["temp_msgs"].append(bot_msg.message_id)
    return SELECTING_TAG

async def tag_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_tag = query.data
    context.user_data["tag"] = selected_tag
    
    await query.edit_message_text(
        text=f"ট্যাগ: **{selected_tag.capitalize()}**\n\nএখন বিষয় বা টাস্কের নাম লিখে পাঠান (যেমন: CSE 112):",
        parse_mode="Markdown"
    )
    return ENTERING_TITLE

async def title_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["temp_msgs"].append(update.message.message_id)
    context.user_data["title"] = update.message.text
    
    cal_markup = hp.create_calendar()
    thread_id = update.message.message_thread_id if update.message else None
    
    bot_msg = await update.message.reply_text(
        "📅 **ক্যালেন্ডার থেকে ডেডলাইনের তারিখ সিলেক্ট করুন:**",
        reply_markup=cal_markup,
        parse_mode="Markdown",
        message_thread_id=thread_id
    )
    context.user_data["temp_msgs"].append(bot_msg.message_id)
    return SELECTING_DATE

async def calendar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "CAL_IGNORE":
        await query.answer()
        return SELECTING_DATE

    if data.startswith("CAL_PREV_"):
        await query.answer()
        _, _, year, month = data.split("_")
        year, month = int(year), int(month)
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        await query.edit_message_reply_markup(reply_markup=hp.create_calendar(year, month))
        return SELECTING_DATE

    if data.startswith("CAL_NEXT_"):
        await query.answer()
        _, _, year, month = data.split("_")
        year, month = int(year), int(month)
        month += 1
        if month > 12:
            month = 1
            year += 1
        await query.edit_message_reply_markup(reply_markup=hp.create_calendar(year, month))
        return SELECTING_DATE

    if data.startswith("CAL_DAY_"):
        _, _, year, month, day = data.split("_")
        selected_date = date(int(year), int(month), int(day))

        # অতীতের তারিখ চেক
        if selected_date < date.today():
            await query.answer("❌ অতীতের কোনো তারিখ সিলেক্ট করা যাবে না!", show_alert=True)
            return SELECTING_DATE

        await query.answer()
        context.user_data["date_str"] = selected_date.strftime("%Y-%m-%d")
        context.user_data["weekday_str"] = selected_date.strftime("%A")

        await query.edit_message_text(
            f"📅 তারিখ: **{context.user_data['date_str']} ({context.user_data['weekday_str']})**\n\n"
            f"📝 কোনো নির্দিষ্ট **নোট বা কমেন্ট** যোগ করতে চান?\n*(না থাকলে `/skip` লিখুন)*",
            parse_mode="Markdown"
        )
        return ENTERING_COMMENT

async def comment_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["temp_msgs"].append(update.message.message_id)
    user_input = update.message.text.strip()
    
    comment = None if user_input.lower() == "/skip" else user_input

    tag = context.user_data.get("tag", "Other")
    title = context.user_data.get("title", "No Title")
    date_str = context.user_data.get("date_str")
    weekday_str = context.user_data.get("weekday_str")
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None

    conn = sqlite3.connect("notices.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notices (chat_id, thread_id, tag, title, comment, due_date, weekday) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (chat_id, thread_id, tag, title, comment, date_str, weekday_str)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    temp_msgs = context.user_data.get("temp_msgs", [])
    await hp.clean_temp_messages(chat_id, temp_msgs, context.bot)

    countdown_text = hp.get_detailed_countdown(date_str)
    
    final_msg = (
        f"📌 **{tag.capitalize()} Notice** `[ID: {task_id}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 **বিষয়:** {title}\n"
        f"📅 **তারিখ:** {date_str} ({weekday_str})\n"
        f"⏳ **সময়:** {countdown_text}\n"
    )
    if comment:
        final_msg += f"💬 **নোট:** \"_{comment}_\"\n"
        
    final_msg += f"━━━━━━━━━━━━━━━━━━━━\n🔔 *ডেডলাইনের ১ দিন আগে স্বয়ংক্রিয় রিমাইন্ডার পাবেন।*"

    kwargs = {"chat_id": chat_id, "text": final_msg, "parse_mode": "Markdown"}
    if thread_id: kwargs["message_thread_id"] = thread_id
        
    await context.bot.send_message(**kwargs)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    temp_msgs = context.user_data.get("temp_msgs", [])
    if update.message:
        temp_msgs.append(update.message.message_id)
    await hp.clean_temp_messages(chat_id, temp_msgs, context.bot)
    
    thread_id = update.message.message_thread_id if update.message else None
    await update.message.reply_text("বাতিল করা হয়েছে।", message_thread_id=thread_id)
    return ConversationHandler.END

async def show_list_by_tag(update: Update, context: ContextTypes.DEFAULT_TYPE, tag: str, tag_name: str):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None
    
    # ইউজারের দেওয়া কমান্ড (/exam, /all ইত্যাদি) সাথে সাথেই মুছে ফেলা
    if update.message:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except Exception:
            pass

    items = db.fetch_notices(chat_id, tag)
    
    # যদি কোনো নোটিস না থাকে (১০ সেকেন্ড পর ডিলিট হবে)
    if not items:
        bot_msg = await context.bot.send_message(
            chat_id=chat_id, 
            text=f"বর্তমানে কোনো পেন্ডিং **{tag_name}** নেই!", 
            parse_mode="Markdown", 
            message_thread_id=thread_id
        )
        asyncio.create_task(hp.delete_after_delay(chat_id, [bot_msg.message_id], context.bot, 10))
        return

    # নোটিস থাকলে সেটা স্থায়ীভাবে থেকে যাবে
    msg = f"📋 **পেন্ডিং {tag_name} তালিকা:**\n\n"
    for item_id, item_tag, title, comment, due_date, weekday in items:
        countdown_text = hp.get_detailed_countdown(due_date)
        
        msg += f"• `[ID: {item_id}]` **{title}**\n"
        msg += f"  📅 তারিখ: {due_date} ({weekday})\n"
        msg += f"  ⏳ বাকি: {countdown_text}\n"
        if comment:
            msg += f"  💬 নোট: \"_{comment}_\"\n"
        msg += "\n"

    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", message_thread_id=thread_id)

async def list_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_list_by_tag(update, context, "exam", "Exam")

async def list_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_list_by_tag(update, context, "assignment", "Assignment")

async def list_presentation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_list_by_tag(update, context, "presentation", "Presentation")

async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_list_by_tag(update, context, None, "সকল নোটিস")

async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message else None
    
    # ইউজারের /done কমান্ড সাথে সাথেই মুছে ফেলা
    if update.message:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except Exception:
            pass

    if not context.args:
        bot_msg = await context.bot.send_message(chat_id=chat_id, text="ব্যবহারের নিয়ম: `/done <ID>` (যেমন: `/done 1`)", parse_mode="Markdown", message_thread_id=thread_id)
        asyncio.create_task(hp.delete_after_delay(chat_id, [bot_msg.message_id], context.bot, 10))
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        bot_msg = await context.bot.send_message(chat_id=chat_id, text="সঠিক আইডি নম্বর দিন!", message_thread_id=thread_id)
        asyncio.create_task(hp.delete_after_delay(chat_id, [bot_msg.message_id], context.bot, 10))
        return

    conn = sqlite3.connect("notices.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notices WHERE id = ? AND chat_id = ?", (task_id, update.effective_chat.id))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    # কাজ সম্পন্ন হওয়ার মেসেজ (১০ সেকেন্ড পর ডিলিট হবে)
    if deleted:
        bot_msg = await context.bot.send_message(chat_id=chat_id, text=f"✅ ID `{task_id}` সফলভাবে তালিকা থেকে মুছে ফেলা হয়েছে!", parse_mode="Markdown", message_thread_id=thread_id)
    else:
        bot_msg = await context.bot.send_message(chat_id=chat_id, text="এই আইডির কোনো নোটিস পাওয়া যায়নি।", message_thread_id=thread_id)
        
    asyncio.create_task(hp.delete_after_delay(chat_id, [bot_msg.message_id], context.bot, 10))