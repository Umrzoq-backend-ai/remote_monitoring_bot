#!/usr/bin/env python3
# ================================================
# bot.py — Ekran boshqarish Telegram boti
# Masofadan: qulflash, uyqu, yoqish, timeout
# ================================================

import subprocess
import logging
import os
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)

# --- SOZLAMALAR ---
BOT_TOKEN = "8809139953:AAFjU58z6PLWg4OLnzc0uEGQ_-kr45iKkG4"
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "screen_control.sh")
OWNER_ID = 5580566610  # Faqat shu Telegram ID boshqara oladi

# ConversationHandler holati
WAITING_CUSTOM_TIME = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- OWNER TEKSHIRUVI ---
def parse_time_value(val):
    """Vaqt stringini soniyaga o'girish: 30s, 15m, 2h"""
    number = int(re.sub(r'[^0-9]', '', val))
    unit = re.sub(r'[0-9]', '', val).lower()
    if unit in ('s', 'sec'):
        return number
    elif unit in ('m', 'min'):
        return number * 60
    elif unit in ('h', 'soat'):
        return number * 3600
    return number * 60  # default minutes


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            username = update.effective_user.username or "noma'lum"
            logger.warning(f"⛔ Ruxsatsiz kirish - ID: {user_id}, @{username}")
            if update.message:
                await update.message.reply_text("⛔ *Access Denied.*", parse_mode="Markdown")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Access Denied.", show_alert=True)
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


# --- BUYRUQ ISHGA TUSHIRISH ---
def run_cmd(command, shell=False):
    try:
        env = {**os.environ, "DISPLAY": ":0", "XAUTHORITY": f"/home/{os.getlogin()}/.Xauthority"}
        if shell:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10, env=env)
        else:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, env=env)
        output = result.stdout.strip() or result.stderr.strip()
        return output if output else "✅ Bajarildi"
    except subprocess.TimeoutExpired:
        return "⚠️ Timeout: javob bermadi"
    except Exception as e:
        return f"❌ Xato: {e}"


def run_script(*args):
    return run_cmd(["bash", SCRIPT_PATH, *args])


# --- CHIROYLI HOLAT ---
def get_status_text():
    env = {**os.environ, "DISPLAY": ":0"}

    # KDE kscreenlocker timeout
    try:
        kde_autolock = subprocess.run(
            ["kreadconfig5", "--file", "kscreenlockerrc", "--group", "Daemon", "--key", "Autolock"],
            capture_output=True, text=True
        ).stdout.strip()
        kde_timeout = subprocess.run(
            ["kreadconfig5", "--file", "kscreenlockerrc", "--group", "Daemon", "--key", "Timeout"],
            capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        kde_autolock = "?"
        kde_timeout = "?"

    if kde_autolock == "true" and kde_timeout:
        timeout_min = int(kde_timeout)
        if timeout_min < 60:
            timeout_str = f"{timeout_min} daqiqa ⏱"
        else:
            h = timeout_min // 60
            m = timeout_min % 60
            timeout_str = f"{h} soat {m} daqiqa ⏱" if m else f"{h} soat ⏱"
    elif kde_autolock == "false":
        timeout_str = "O'chirilgan 🔴"
    else:
        timeout_str = "Aniqlanmadi ❓"

    # Ekran holati
    try:
        xset_out = subprocess.run(
            ["xset", "q"], capture_output=True, text=True, env=env
        ).stdout
        screen_str = "Yoqiq ☀️" if "Monitor is On" in xset_out else "O'chiq 😴"
    except Exception:
        screen_str = "Aniqlanmadi"

    # xprintidle
    try:
        idle_ms = int(subprocess.run(
            ["xprintidle"], capture_output=True, text=True, env=env
        ).stdout.strip())
        idle_min = idle_ms // 60000
        idle_str = f"{idle_min} daqiqa" if idle_min > 0 else f"{idle_ms // 1000} soniya"
    except Exception:
        idle_str = "?"

    # Keep-alive holati
    keep_alive_pid = "/tmp/screen_keep_alive.pid"
    if os.path.exists(keep_alive_pid):
        try:
            with open(keep_alive_pid) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # Check if alive
            keep_str = "🟢 ISHLAYAPTI"
        except (ProcessLookupError, ValueError, OSError):
            keep_str = "🔴 O'CHIQ"
    else:
        keep_str = "🔴 O'CHIQ"

    # idletimed holati
    try:
        result = subprocess.run(["pgrep", "-f", "idletimed"], capture_output=True, text=True)
        idle_daemon = "⚠️ ISHLAYAPTI" if result.returncode == 0 else "✅ O'CHIQ"
    except Exception:
        idle_daemon = "?"

    # Lock timer holati (fayl orqali)
    lock_timer_str = ""
    lock_timer_file = "/tmp/screen_lock_timer_end.txt"
    if os.path.exists(lock_timer_file):
        try:
            with open(lock_timer_file) as f:
                end_ts = int(f.read().strip())
            remaining = end_ts - int(time.time())
            if remaining > 0:
                h = remaining // 3600
                m = (remaining % 3600) // 60
                if h > 0:
                    lock_timer_str = f"\n🔒 Lock timer: *{h}s {m}d qoldi*"
                else:
                    lock_timer_str = f"\n🔒 Lock timer: *{m} daqiqa qoldi*"
        except Exception:
            pass

    return (
        "📊 *Kompyuter holati*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🖥  Ekran:       {screen_str}\n"
        f"⏱  Timeout:    {timeout_str}\n"
        f"⏳ Idle:        {idle_str}\n"
        f"🟢 Keep-alive: {keep_str}\n"
        f"🤖 idletimed:  {idle_daemon}\n"
        f"🔋 Tizim:       Ishlamoqda ✅"
        f"{lock_timer_str}\n"
        "━━━━━━━━━━━━━━━━━━"
    )


# --- KLAVIATURALAR ---
def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Holat",           callback_data="status"),
            InlineKeyboardButton("🔓 Qulfni och",       callback_data="unlock"),
        ],
        [
            InlineKeyboardButton("🔒 Hozir quflash",    callback_data="lock"),
            InlineKeyboardButton("🔒⏱ Vaqtga quflash",  callback_data="menu_lock_timer"),
        ],
        [
            InlineKeyboardButton("😴 Uyqu",             callback_data="sleep"),
            InlineKeyboardButton("☀️ Ekran yoq",        callback_data="wake"),
        ],
        [
            InlineKeyboardButton("⏱ Timeout",           callback_data="menu_timeout"),
            InlineKeyboardButton("🔴 Timeout o'chir",    callback_data="off"),
        ],
        [
            InlineKeyboardButton("🟢 Keep-alive",       callback_data="keep_alive"),
            InlineKeyboardButton("🛑 Stop alive",        callback_data="stop_alive"),
        ],
        [
            InlineKeyboardButton("🚪 Chiqarib yubor",   callback_data="logout_confirm"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def lock_timer_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("30 daqiqa",  callback_data="lock_timer_30m"),
            InlineKeyboardButton("1 soat",     callback_data="lock_timer_1h"),
            InlineKeyboardButton("2 soat",     callback_data="lock_timer_2h"),
        ],
        [
            InlineKeyboardButton("3 soat",     callback_data="lock_timer_3h"),
            InlineKeyboardButton("4 soat",     callback_data="lock_timer_4h"),
            InlineKeyboardButton("5 soat",     callback_data="lock_timer_5h"),
        ],
        [
            InlineKeyboardButton("6 soat",     callback_data="lock_timer_6h"),
            InlineKeyboardButton("8 soat",     callback_data="lock_timer_8h"),
            InlineKeyboardButton("12 soat",    callback_data="lock_timer_12h"),
        ],
        [
            InlineKeyboardButton("✏️ O'zim yozaman", callback_data="custom_lock_timer"),
        ],
        [
            InlineKeyboardButton("⬅️ Orqaga",  callback_data="back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def timeout_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("30 soniya",   callback_data="timeout_30s"),
            InlineKeyboardButton("1 daqiqa",    callback_data="timeout_1m"),
            InlineKeyboardButton("5 daqiqa",    callback_data="timeout_5m"),
        ],
        [
            InlineKeyboardButton("10 daqiqa",   callback_data="timeout_10m"),
            InlineKeyboardButton("15 daqiqa",   callback_data="timeout_15m"),
            InlineKeyboardButton("30 daqiqa",   callback_data="timeout_30m"),
        ],
        [
            InlineKeyboardButton("1 soat",      callback_data="timeout_1h"),
            InlineKeyboardButton("2 soat",      callback_data="timeout_2h"),
            InlineKeyboardButton("5 soat",      callback_data="timeout_5h"),
        ],
        [
            InlineKeyboardButton("12 soat",     callback_data="timeout_12h"),
            InlineKeyboardButton("24 soat",     callback_data="timeout_24h"),
            InlineKeyboardButton("🔴 O'chir",   callback_data="off"),
        ],
        [
            # O'zim yozaman tugmasi
            InlineKeyboardButton("✏️ O'zim yozaman",  callback_data="custom_timeout"),
        ],
        [
            InlineKeyboardButton("⬅️ Orqaga",   callback_data="back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(action):
    keyboard = [[
        InlineKeyboardButton("✅ Ha, bajar",  callback_data=f"confirm_{action}"),
        InlineKeyboardButton("❌ Bekor qil",  callback_data="back"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard():
    keyboard = [[
        InlineKeyboardButton("❌ Bekor qil", callback_data="back"),
    ]]
    return InlineKeyboardMarkup(keyboard)


# --- BUYRUQLAR ---

@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "noma'lum"
    logger.info(f"🔑 /start - User ID: {user_id}, Username: @{username}")
    text = (
        "🖥️ *Ekran Masofadan Boshqaruv Boti*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📊 /status — hozirgi holat\n"
        "🔒 /lock — ekranni quflash\n"
        "😴 /sleep — uyqu rejimi\n"
        "☀️ /wake — ekranni yoqish\n"
        "🔴 /off — timeoutni o'chirish\n"
        "⏱ /timeout — vaqt belgilash\n"
        "🟢 /keep\\_alive — auto-logout oldini olish\n"
        "🛑 /stop\\_alive — keep-alive to'xtatish\n\n"
        "⏱ *Timeout misollari:*\n"
        "`/timeout 30s` — 30 soniya\n"
        "`/timeout 15m` — 15 daqiqa\n"
        "`/timeout 2h`  — 2 soat\n"
        "`/timeout 24h` — 24 soat\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Yoki quyidagi tugmalardan foydalaning 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())



@owner_only
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_status_text(), parse_mode="Markdown", reply_markup=main_keyboard())



@owner_only
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("lock")
    await update.message.reply_text(f"🔒 {result}", reply_markup=main_keyboard())



@owner_only
async def sleep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("sleep")
    await update.message.reply_text(f"😴 {result}", reply_markup=main_keyboard())



@owner_only
async def wake_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("wake")
    await update.message.reply_text(f"☀️ {result}", reply_markup=main_keyboard())



@owner_only
async def off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("off")
    await update.message.reply_text(f"🔴 {result}", reply_markup=main_keyboard())



@owner_only
async def timeout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "⏱ *Timeout tanlang yoki o'zingiz yozing:*\n\n"
            "Misol: `/timeout 30s` `/timeout 15m` `/timeout 2h`",
            parse_mode="Markdown",
            reply_markup=timeout_keyboard()
        )
        return
    val = args[0]
    result = run_script("timeout", val)
    await update.message.reply_text(f"⏱ {result}", reply_markup=main_keyboard())



@owner_only
async def logout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚪 *Haqiqatan ham chiqarib yuborasizmi?*",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard("logout")
    )



@owner_only
async def lock_timer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "🔒⏱ *Qancha vaqtga quflash?*\n\nMisol: `/lock_timer 4h`",
            parse_mode="Markdown",
            reply_markup=lock_timer_keyboard()
        )
        return
    val = args[0]
    result = run_script("lock_timer", val)

    # Vaqtni hisoblash
    seconds = parse_time_value(val)
    end_time = int(subprocess.run(["date", "+%s"], capture_output=True, text=True).stdout.strip()) + seconds

    # Saqlash (status uchun)
    context.bot_data["lock_timer_end"] = end_time
    context.bot_data["lock_timer_val"] = val
    context.bot_data["lock_timer_chat_id"] = update.effective_chat.id

    await update.message.reply_text(
        f"🔒 *Ekran {val} ga qulflandi!*\n{result}\n\n"
        f"⚠️ Vaqt tugagach avtomatik *LOGOUT* bo'lasiz!\n"
        f"📩 Vaqt tugaganda sizga xabar keladi.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    # Background task: vaqt tugaganda xabar yuborish
    if "lock_timer_job" in context.bot_data:
        old_job = context.bot_data["lock_timer_job"]
        old_job.schedule_removal()

    job = context.job_queue.run_once(
        lock_timer_finished_callback,
        when=seconds,
        chat_id=update.effective_chat.id,
        data={"val": val}
    )
    context.bot_data["lock_timer_job"] = job

    # Har 10 daqiqada qolgan vaqtni xabar qilish
    if "lock_timer_repeat_job" in context.bot_data:
        old_job = context.bot_data["lock_timer_repeat_job"]
        old_job.schedule_removal()

    # Faqat 1 soatdan ko'p bo'lsa har 30 daqiqada, aks holda har 10 daqiqada
    interval = 1800 if seconds > 3600 else 600
    repeat_job = context.job_queue.run_repeating(
        lock_timer_status_callback,
        interval=interval,
        first=interval,
        chat_id=update.effective_chat.id,
        data={"end_time": end_time, "val": val}
    )
    context.bot_data["lock_timer_repeat_job"] = repeat_job


async def lock_timer_finished_callback(context: ContextTypes.DEFAULT_TYPE):
    """Vaqt tugaganda xabar yuborish"""
    job = context.job
    val = job.data["val"]
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=(
            f"⏰ *Vaqt tugadi!*\n\n"
            f"🔒 {val} davomida qulflangan edi.\n"
            f"🚪 Hozir *LOGOUT* qilindi.\n\n"
            f"━━━━━━━━━━━━━━━━━━"
        ),
        parse_mode="Markdown"
    )
    # Repeat job ni to'xtatish
    if "lock_timer_repeat_job" in context.bot_data:
        context.bot_data["lock_timer_repeat_job"].schedule_removal()
        del context.bot_data["lock_timer_repeat_job"]
    # Tozalash
    context.bot_data.pop("lock_timer_end", None)
    context.bot_data.pop("lock_timer_val", None)
    context.bot_data.pop("lock_timer_job", None)


async def lock_timer_status_callback(context: ContextTypes.DEFAULT_TYPE):
    """Har X daqiqada qolgan vaqtni xabar qilish"""
    job = context.job
    end_time = job.data["end_time"]
    val = job.data["val"]

    remaining = end_time - int(time.time())
    if remaining <= 0:
        job.schedule_removal()
        return

    # Qolgan vaqtni chiroyli formatlash
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    if hours > 0:
        remaining_str = f"{hours} soat {minutes} daqiqa"
    else:
        remaining_str = f"{minutes} daqiqa"

    await context.bot.send_message(
        chat_id=job.chat_id,
        text=(
            f"⏱ *Lock timer holati*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔒 Qulflangan: {val}\n"
            f"⏳ Qolgan vaqt: *{remaining_str}*\n"
            f"🟢 Keep-alive: ishlayapti\n"
            f"━━━━━━━━━━━━━━━━━━"
        ),
        parse_mode="Markdown"
    )



@owner_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("unlock")
    await update.message.reply_text(f"🔓 {result}", reply_markup=main_keyboard())


@owner_only
async def keep_alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("keep_alive")
    await update.message.reply_text(
        f"🟢 *Keep-alive ishga tushdi!*\n{result}\n\n"
        "ℹ️ idletimed sizi auto-logout qilmaydi.\n"
        "🛑 /stop\\_alive bilan to'xtatish mumkin.",
        parse_mode="Markdown", reply_markup=main_keyboard()
    )


@owner_only
async def stop_alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = run_script("stop_alive")
    await update.message.reply_text(f"🛑 {result}", reply_markup=main_keyboard())


# --- O'ZIM YOZAMAN: ConversationHandler ---
async def custom_timeout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi 'O'zim yozaman' tugmasini bosdi"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ *Qancha vaqt?*\n\n"
        "Quyidagi formatda yozing:\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⏱ `45s`  — 45 soniya\n"
        "⏱ `20m`  — 20 daqiqa\n"
        "⏱ `3h`   — 3 soat\n"
        "⏱ `90m`  — 1 soat 30 daqiqa\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Xohlagan vaqtni yozing 👇",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )
    return WAITING_CUSTOM_TIME


async def custom_timeout_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi vaqtni yozdi"""
    text = update.message.text.strip().lower()

    # Validatsiya: raqam + s/m/h bo'lishi kerak
    if not re.match(r'^\d+[smh]$', text):
        await update.message.reply_text(
            "❌ *Noto'g'ri format!*\n\n"
            "To'g'ri misol: `30s`, `15m`, `2h`\n"
            "Yana urinib ko'ring 👇",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        return WAITING_CUSTOM_TIME

    result = run_script("timeout", text)
    await update.message.reply_text(
        f"✅ *Timeout o'rnatildi:* `{text}`\n{result}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


async def custom_timeout_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi", reply_markup=main_keyboard())
    return ConversationHandler.END


# --- INLINE TUGMA HANDLER ---

@owner_only
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "status":
        text = get_status_text()
        keyboard = main_keyboard()

    elif data == "lock":
        result = run_script("lock")
        text = f"🔒 *Ekran qulflandi!*\n{result}"
        keyboard = main_keyboard()

    elif data == "unlock":
        result = run_script("unlock")
        text = f"🔓 *Qulf ochildi!*\n{result}"
        keyboard = main_keyboard()
        # Lock timer job-larni bekor qilish
        if "lock_timer_job" in context.bot_data:
            context.bot_data["lock_timer_job"].schedule_removal()
            del context.bot_data["lock_timer_job"]
        if "lock_timer_repeat_job" in context.bot_data:
            context.bot_data["lock_timer_repeat_job"].schedule_removal()
            del context.bot_data["lock_timer_repeat_job"]
        context.bot_data.pop("lock_timer_end", None)
        context.bot_data.pop("lock_timer_val", None)

    elif data == "menu_lock_timer":
        text = (
            "🔒⏱ *Qancha vaqtga quflash?*\n\n"
            "Belgilangan vaqt o'tgach ekran\n"
            "avtomatik qulfdan chiqadi.\n\n"
            "✏️ *O'zim yozaman* — istalgan vaqtni kiriting"
        )
        keyboard = lock_timer_keyboard()

    elif data.startswith("lock_timer_"):
        val = data.replace("lock_timer_", "")
        result = run_script("lock_timer", val)
        text = (
            f"🔒 *Ekran {val} ga qulflandi!*\n\n"
            f"{result}\n\n"
            "⚠️ Vaqt tugagach avtomatik *LOGOUT* bo'lasiz!\n"
            "📩 Vaqt tugaganda xabar keladi.\n"
            "Bekor qilish uchun 🔓 tugmasini bosing."
        )
        keyboard = main_keyboard()

        # Job queue: vaqt tugaganda xabar
        seconds = parse_time_value(val)
        end_time = int(time.time()) + seconds
        context.bot_data["lock_timer_end"] = end_time
        context.bot_data["lock_timer_val"] = val

        if "lock_timer_job" in context.bot_data:
            context.bot_data["lock_timer_job"].schedule_removal()
        if "lock_timer_repeat_job" in context.bot_data:
            context.bot_data["lock_timer_repeat_job"].schedule_removal()

        job = context.job_queue.run_once(
            lock_timer_finished_callback,
            when=seconds,
            chat_id=query.message.chat_id,
            data={"val": val}
        )
        context.bot_data["lock_timer_job"] = job

        interval = 1800 if seconds > 3600 else 600
        repeat_job = context.job_queue.run_repeating(
            lock_timer_status_callback,
            interval=interval,
            first=interval,
            chat_id=query.message.chat_id,
            data={"end_time": end_time, "val": val}
        )
        context.bot_data["lock_timer_repeat_job"] = repeat_job

    elif data == "custom_lock_timer":
        await query.edit_message_text(
            "✏️ *Qancha vaqtga quflash?*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⏱ `30m`  — 30 daqiqa\n"
            "⏱ `4h`   — 4 soat\n"
            "⏱ `90m`  — 1 soat 30 daqiqa\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Yoki: `/lock_timer 4h` deb yozing 👇",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        context.user_data["waiting_lock_timer"] = True
        return

    elif data == "sleep":
        result = run_script("sleep")
        text = f"😴 *Uyqu rejimi yoqildi*\n{result}"
        keyboard = main_keyboard()

    elif data == "wake":
        result = run_script("wake")
        text = f"☀️ *Ekran yoqildi*\n{result}"
        keyboard = main_keyboard()

    elif data == "off":
        result = run_script("off")
        text = f"🔴 *Timeout o'chirildi*\n{result}"
        keyboard = main_keyboard()

    elif data == "menu_timeout":
        text = (
            "⏱ *Timeout vaqtini tanlang:*\n\n"
            "Tayyor vaqtlardan tanlang yoki\n"
            "✏️ *O'zim yozaman* tugmasini bosing"
        )
        keyboard = timeout_keyboard()

    elif data == "custom_timeout":
        # ConversationHandler bu yerda ishlamaydi, shuning uchun inline xabar
        await query.edit_message_text(
            "✏️ *Qancha vaqt?*\n\n"
            "Quyidagi formatda yozing:\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⏱ `45s`  — 45 soniya\n"
            "⏱ `20m`  — 20 daqiqa\n"
            "⏱ `3h`   — 3 soat\n"
            "⏱ `90m`  — 1 soat 30 daqiqa\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Yoki: `/timeout 45m` deb yozing 👇",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard()
        )
        context.user_data["waiting_timeout"] = True
        return

    elif data.startswith("timeout_"):
        val = data.replace("timeout_", "")
        result = run_script("timeout", val)
        text = f"⏱ *Timeout o'rnatildi:* `{val}`\n{result}"
        keyboard = main_keyboard()

    elif data == "logout_confirm":
        text = "🚪 *Haqiqatan ham chiqarib yuborasizmi?*\nBarcha ochiq dasturlar yopiladi!"
        keyboard = confirm_keyboard("logout")

    elif data == "keep_alive":
        result = run_script("keep_alive")
        text = (
            "🟢 *Keep-alive ishga tushdi!*\n\n"
            f"{result}\n\n"
            "ℹ️ Har 50 sek idle reset qilinadi.\n"
            "⚡ idletimed sizi auto-logout qilmaydi.\n"
            "🛑 To'xtatish uchun *Stop alive* bosing."
        )
        keyboard = main_keyboard()

    elif data == "stop_alive":
        result = run_script("stop_alive")
        text = f"🛑 *Keep-alive to'xtatildi*\n{result}"
        keyboard = main_keyboard()

    elif data == "confirm_logout":
        result = run_cmd("loginctl terminate-user $USER", shell=True)
        text = f"🚪 *Foydalanuvchi chiqarib yuborildi!*\n{result}"
        keyboard = main_keyboard()

    elif data == "back":
        text = "🖥️ *Asosiy menyu:*"
        keyboard = main_keyboard()
        context.user_data["waiting_timeout"] = False

    else:
        text = "❓ Noma'lum buyruq"
        keyboard = main_keyboard()

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)


# --- MATN XABAR HANDLER (custom timeout uchun) ---

@owner_only
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    # --- Lock timer uchun ---
    if context.user_data.get("waiting_lock_timer"):
        if not re.match(r'^\d+[smh]$', text):
            await update.message.reply_text(
                "❌ *Noto'g'ri format!*\n\nTo'g'ri: `30m`, `4h`, `90m`",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            return
        context.user_data["waiting_lock_timer"] = False
        result = run_script("lock_timer", text)
        await update.message.reply_text(
            f"🔒 *Ekran {text} ga qulflandi!*\n{result}\n\n⚠️ Vaqt tugagach avtomatik *LOGOUT* bo'lasiz!\nBekor qilish uchun 🔓 tugmasini bosing.",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
        return

    # --- Timeout uchun ---
    if context.user_data.get("waiting_timeout"):
        if not re.match(r'^\d+[smh]$', text):
            await update.message.reply_text(
                "❌ *Noto'g'ri format!*\n\nTo'g'ri: `30s`, `15m`, `2h`",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            return
        context.user_data["waiting_timeout"] = False
        result = run_script("timeout", text)
        await update.message.reply_text(
            f"✅ *Timeout o'rnatildi:* `{text}`\n{result}",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )


# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("status",     status_cmd))
    app.add_handler(CommandHandler("lock",       lock_cmd))
    app.add_handler(CommandHandler("lock_timer", lock_timer_cmd))
    app.add_handler(CommandHandler("unlock",     unlock_cmd))
    app.add_handler(CommandHandler("keep_alive", keep_alive_cmd))
    app.add_handler(CommandHandler("stop_alive", stop_alive_cmd))
    app.add_handler(CommandHandler("sleep",      sleep_cmd))
    app.add_handler(CommandHandler("wake",       wake_cmd))
    app.add_handler(CommandHandler("off",        off_cmd))
    app.add_handler(CommandHandler("timeout",    timeout_cmd))
    app.add_handler(CommandHandler("logout",     logout_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    logger.info("🤖 Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
