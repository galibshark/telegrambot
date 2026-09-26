import calendar
import asyncio
from datetime import datetime, date, timedelta, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# বাংলাদেশ টাইমজোন ডিরেক্টলি সেট করা (UTC +6 ঘণ্টা)
BD_TZ = timezone(timedelta(hours=6))

async def clean_temp_messages(chat_id: int, msg_ids: list, bot):
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass

def create_calendar(year=None, month=None):
    now = datetime.now(BD_TZ)
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    keyboard = []
    month_name = calendar.month_name[month]
    
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=f"CAL_PREV_{year}_{month}"),
        InlineKeyboardButton(f"{month_name} {year}", callback_data="CAL_IGNORE"),
        InlineKeyboardButton("▶️", callback_data=f"CAL_NEXT_{year}_{month}")
    ])

    week_days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    keyboard.append([InlineKeyboardButton(day, callback_data="CAL_IGNORE") for day in week_days])

    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="CAL_IGNORE"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"CAL_DAY_{year}_{month}_{day}"))
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)

def get_detailed_countdown(target_date_str):
    # ডেডলাইন রাত ১২:০০ AM, বাংলাদেশ টাইমজোন অনুযায়ী সেট করা হলো
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=BD_TZ)
    
    # বর্তমান সময় ল্যাপটপ থেকে না নিয়ে গ্লোবাল বাংলাদেশ টাইমজোন থেকে নেওয়া হলো
    now = datetime.now(BD_TZ)
    diff = target_dt - now
    
    if diff.total_seconds() <= 0:
        return "আজকেই ডেডলাইন!"
    
    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    if days > 0:
        return f"{days} দিন {hours} ঘণ্টা {minutes} মিনিট বাকি"
    elif hours > 0:
        return f"{hours} ঘণ্টা {minutes} মিনিট বাকি"
    else:
        return f"{minutes} মিনিট বাকি"

async def delete_after_delay(chat_id: int, msg_ids: list, bot, delay: int):
    await asyncio.sleep(delay)
    for mid in msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass