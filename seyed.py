import logging
import os
from pathlib import Path
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

import database

TEMP_ADMIN_IDS = {234368567}

(
    ADMIN_PANEL_MAIN,
    ADMIN_PANEL_SETTINGS,
    ADMIN_PANEL_MANAGE,
    ADMIN_PANEL_ADD_PHONE,
    ADMIN_PANEL_REMOVE_PHONE,
) = range(5)

REQUEST_CONTACT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("ارسال شماره موبایل", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="لطفاً شماره موبایل خود را ارسال کنید",
)


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("تنظیمات ربات ⚙️", callback_data="panel:settings")],
            [InlineKeyboardButton("بازگشت به ربات ⬅️", callback_data="panel:back")],
        ]
    )


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "مدیریت ادمین‌ها 🧑‍💼", callback_data="settings:manage"
                )
            ],
            [InlineKeyboardButton("بازگشت 🔙", callback_data="settings:back")],
        ]
    )


def admin_manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("افزودن ادمین ➕", callback_data="manage:add"),
                InlineKeyboardButton("حذف ادمین ➖", callback_data="manage:remove"),
            ],
            [InlineKeyboardButton("لیست ادمین‌ها 📋", callback_data="manage:list")],
            [InlineKeyboardButton("بازگشت 🔙", callback_data="manage:back")],
        ]
    )


def admin_add_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("انصراف 🔙", callback_data="add:cancel")]]
    )

USER_MENU_RESPONSES = {
    "Case Studies": "بخش Case Studies به زودی در دسترس قرار می‌گیرد.",
    "وبینار ها": "وبینارهای جدید به زودی اعلام می‌شوند.",
    "دراپ لرنینگ": "دراپ لرنینگ به زودی فعال می‌شود.",
    "مشاوره رایگان": "مشاوران ما به زودی پاسخگوی شما خواهند بود.",
    "خدمات": "لیست خدمات به زودی در دسترس خواهد بود.",
}


def load_env() -> None:
    """Load key/value pairs from a local .env file into os.environ."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it in the environment or in the .env file."
        )
    return token


def is_admin_user(telegram_id: int) -> bool:
    return telegram_id in TEMP_ADMIN_IDS or database.is_admin(telegram_id)


async def ensure_registered_user(
    update: Update,
) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return False

    if database.user_has_phone(user_id):
        return True

    await prompt_for_contact(update)
    return False


async def prompt_for_contact(update: Update) -> None:
    if update.message:
        await update.message.reply_text(
            "برای استفاده از ربات، لطفاً شماره موبایل خود را از طریق دکمه زیر ارسال کنید.",
            reply_markup=REQUEST_CONTACT_KEYBOARD,
        )


def build_main_menu_keyboard(user_id: Optional[int]) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton("Case Studies")],
        [KeyboardButton("وبینار ها")],
        [KeyboardButton("دراپ لرنینگ")],
        [KeyboardButton("مشاوره رایگان")],
        [KeyboardButton("خدمات")],
    ]
    if user_id is not None and is_admin_user(user_id):
        rows.append([KeyboardButton("🛠️ پنل ادمین")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def send_main_menu(update: Update) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if update.message:
        await update.message.reply_text(
            "سلام! یکی از گزینه‌های زیر را انتخاب کن:",
            reply_markup=build_main_menu_keyboard(user_id),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_registered_user(update):
        return
    await send_main_menu(update)


def extract_phone_last10(raw_phone: str) -> Optional[str]:
    digits = "".join(ch for ch in raw_phone if ch.isdigit())
    if len(digits) < 10:
        return None
    return digits[-10:]


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.contact:
        return

    user = update.effective_user
    contact = update.message.contact

    if not user or contact.user_id != user.id:
        await update.message.reply_text(
            "لطفاً شماره موبایل متعلق به خودتان را ارسال کنید.",
            reply_markup=REQUEST_CONTACT_KEYBOARD,
        )
        return

    phone_number = extract_phone_last10(contact.phone_number)
    if not phone_number:
        await update.message.reply_text(
            "شماره موبایل معتبر نیست. لطفاً شماره را با فرمت صحیح ارسال کنید.",
            reply_markup=REQUEST_CONTACT_KEYBOARD,
        )
        return

    database.upsert_user(
        telegram_id=user.id,
        phone_number=phone_number,
        fname=user.first_name or "",
        lname=user.last_name or "",
        username=user.username or "",
    )
    await update.message.reply_text(
        "شماره موبایل شما ذخیره شد.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await send_main_menu(update)


async def handle_menu_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await ensure_registered_user(update):
        return

    if update.message:
        user_id = update.effective_user.id if update.effective_user else None
        text = update.message.text or ""
        response = USER_MENU_RESPONSES.get(text, "این بخش به زودی در دسترس قرار می‌گیرد.")
        await update.message.reply_text(
            response,
            reply_markup=build_main_menu_keyboard(user_id),
        )


async def admin_panel_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user = update.effective_user
    if not user or not is_admin_user(user.id):
        if update.message:
            await update.message.reply_text("شما به این بخش دسترسی ندارید.")
        elif update.callback_query:
            query = update.callback_query
            await query.answer("شما به این بخش دسترسی ندارید.", show_alert=True)
        return ConversationHandler.END

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_keyboard(),
        )
    elif update.message:
        await update.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_keyboard(),
        )
    return ADMIN_PANEL_MAIN


async def admin_panel_main_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    data = query.data

    if data == "panel:settings":
        await query.edit_message_text(
            "بخش تنظیمات ربات:",
            reply_markup=admin_settings_keyboard(),
        )
        return ADMIN_PANEL_SETTINGS

    if data == "panel:back":
        await query.edit_message_text("بازگشت به ربات.")
        await send_main_menu(update)
        return ConversationHandler.END

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    return ADMIN_PANEL_MAIN


async def admin_panel_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    data = query.data

    if data == "settings:manage":
        await query.edit_message_text(
            "بخش مدیریت ادمین‌ها:",
            reply_markup=admin_manage_keyboard(),
        )
        return ADMIN_PANEL_MANAGE

    if data == "settings:back":
        await query.edit_message_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_keyboard(),
        )
        return ADMIN_PANEL_MAIN

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    return ADMIN_PANEL_SETTINGS


async def admin_panel_manage_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    data = query.data

    if data == "manage:add":
        await query.edit_message_text(
            "شماره موبایل کاربر را ارسال کنید (۱۰ رقم پایانی).",
            reply_markup=admin_add_cancel_keyboard(),
        )
        return ADMIN_PANEL_ADD_PHONE

    if data == "manage:remove":
        await show_remove_admin_menu(query, context)
        return ADMIN_PANEL_REMOVE_PHONE

    if data == "manage:list":
        await reply_with_admin_list(update, context, edit_message=True)
        await query.edit_message_text(
            "بخش مدیریت ادمین‌ها:",
            reply_markup=admin_manage_keyboard(),
        )
        return ADMIN_PANEL_MANAGE

    if data == "manage:back":
        await query.edit_message_text(
            "بخش تنظیمات ربات:",
            reply_markup=admin_settings_keyboard(),
        )
        return ADMIN_PANEL_SETTINGS

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    return ADMIN_PANEL_MANAGE


async def show_remove_admin_menu(
    query, context: ContextTypes.DEFAULT_TYPE
) -> None:
    admins = [
        record
        for record in database.list_admins()
        if record["telegram_id"] not in TEMP_ADMIN_IDS
    ]

    if not admins:
        await query.edit_message_text(
            "ادمینی برای حذف وجود ندارد.",
            reply_markup=admin_manage_keyboard(),
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"{admin['phone_number']} | {admin['fname'] or 'بدون نام'}",
                callback_data=f"remove:{admin['telegram_id']}",
            )
        ]
        for admin in admins
    ]
    keyboard.append(
        [InlineKeyboardButton("بازگشت 🔙", callback_data="remove:back")]
    )

    await query.edit_message_text(
        "یکی از ادمین‌ها را برای حذف انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def reply_with_admin_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    edit_message: bool = False,
) -> None:
    admins = list(database.list_admins())
    lines = []

    for record in admins:
        phone_display = record["phone_number"] or "نامشخص"
        full_name = " ".join(
            part for part in (record["fname"], record["lname"]) if part
        ).strip() or "بدون نام"
        username = f"@{record['username']}" if record["username"] else "بدون نام کاربری"
        lines.append(
            f"ID: {record['telegram_id']} | شماره: {phone_display} | نام: {full_name} | {username}"
        )

    for temp_admin in TEMP_ADMIN_IDS:
        if not any(admin["telegram_id"] == temp_admin for admin in admins):
            lines.append(f"ID: {temp_admin} | ادمین موقت (خروجی قابل ویرایش نیست)")

    if not lines:
        lines.append("ادمینی ثبت نشده است.")

    text = "\n".join(lines)

    if edit_message and update.callback_query:
        await update.callback_query.message.reply_text(text)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text)
    elif update.message:
        await update.message.reply_text(text)


async def handle_remove_admin_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    data = query.data
    if data == "remove:back":
        await query.edit_message_text(
            "بخش مدیریت ادمین‌ها:",
            reply_markup=admin_manage_keyboard(),
        )
        return ADMIN_PANEL_MANAGE

    try:
        target_id = int(data.split(":", maxsplit=1)[1])
    except (IndexError, ValueError):
        await query.answer("گزینه نامعتبر است.", show_alert=True)
        return ADMIN_PANEL_REMOVE_PHONE

    if target_id in TEMP_ADMIN_IDS:
        await query.edit_message_text(
            "امکان حذف این ادمین وجود ندارد.",
            reply_markup=admin_manage_keyboard(),
        )
        return ADMIN_PANEL_MANAGE

    user_record = database.get_user(target_id)

    if database.remove_admin(target_id):
        await query.edit_message_text(
            "دسترسی ادمین حذف شد.",
            reply_markup=admin_manage_keyboard(),
        )
        await notify_admin_status_change(
            context,
            target_id,
            granted=False,
            phone_number=user_record["phone_number"] if user_record else None,
        )
    else:
        await query.edit_message_text(
            "این کاربر ادمین نیست.",
            reply_markup=admin_manage_keyboard(),
        )

    return ADMIN_PANEL_MANAGE


async def admin_add_phone(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_registered_user(update):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        if update.message:
            await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    phone_input = (update.message.text or "").strip()

    phone_number = extract_phone_last10(phone_input)
    if not phone_number:
        if update.message:
            await update.message.reply_text(
                "شماره موبایل معتبر نیست. لطفاً دوباره شماره را وارد کنید.",
                reply_markup=admin_add_cancel_keyboard(),
            )
        return ADMIN_PANEL_ADD_PHONE

    target_user = database.get_user_by_phone(phone_number)
    if not target_user:
        if update.message:
            await update.message.reply_text(
                "هیچ کاربری با این شماره موبایل در ربات ثبت نشده است.",
                reply_markup=admin_add_cancel_keyboard(),
            )
        return ADMIN_PANEL_ADD_PHONE

    target_id = target_user["telegram_id"]

    if database.is_admin(target_id):
        if update.message:
            await update.message.reply_text(
                "این کاربر هم‌اکنون ادمین است.",
                reply_markup=admin_manage_keyboard(),
            )
        return ADMIN_PANEL_MANAGE

    database.add_admin(target_id)
    if update.message:
        full_name = " ".join(
            part for part in (target_user["fname"], target_user["lname"]) if part
        ).strip() or "بدون نام"
        await update.message.reply_text(
            f"ادمین جدید اضافه شد.\nکاربر: {full_name}",
            reply_markup=admin_manage_keyboard(),
        )

    await notify_admin_status_change(
        context, target_id, granted=True, phone_number=phone_number
    )

    return ADMIN_PANEL_MANAGE


async def admin_add_cancel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "بخش مدیریت ادمین‌ها:",
        reply_markup=admin_manage_keyboard(),
    )
    return ADMIN_PANEL_MANAGE


async def notify_admin_status_change(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_id: int,
    *,
    granted: bool,
    phone_number: Optional[str] = None,
) -> None:
    try:
        status_text = "شما ادمین شدید." if granted else "دسترسی ادمین شما حذف شد."
        message = (
            f"{status_text}\nشماره ثبت‌شده: {phone_number}"
            if phone_number
            else status_text
        )
        await context.bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        logging.warning("Failed to notify user %s about admin status change", telegram_id)


async def admin_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.message:
        await update.message.reply_text(
            "خروج از پنل ادمین.",
        )
        await send_main_menu(update)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("خروج از پنل ادمین.")
        await send_main_menu(update)
    return ConversationHandler.END


def main() -> None:
    load_env()
    database.init_db()
    token = get_bot_token()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    application = Application.builder().token(token).build()

    admin_panel_handler = ConversationHandler(
        entry_points=[
            CommandHandler("panel", admin_panel_entry),
            MessageHandler(
                filters.TEXT & filters.Regex("^🛠️ پنل ادمین$"), admin_panel_entry
            ),
        ],
        states={
            ADMIN_PANEL_MAIN: [
                CallbackQueryHandler(admin_panel_main_callback, pattern="^panel:"),
            ],
            ADMIN_PANEL_SETTINGS: [
                CallbackQueryHandler(admin_panel_settings_callback, pattern="^settings:"),
            ],
            ADMIN_PANEL_MANAGE: [
                CallbackQueryHandler(admin_panel_manage_callback, pattern="^manage:"),
            ],
            ADMIN_PANEL_ADD_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_phone),
                CallbackQueryHandler(admin_add_cancel_callback, pattern="^add:cancel$"),
            ],
            ADMIN_PANEL_REMOVE_PHONE: [
                CallbackQueryHandler(handle_remove_admin_selection, pattern="^remove:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(admin_panel_handler)
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_selection)
    )

    application.run_polling()


if __name__ == "__main__":
    main()

