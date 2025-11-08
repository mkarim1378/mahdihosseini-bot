import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Union

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatMemberStatus, ChatType, ParseMode
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
    ADMIN_PANEL_BROADCAST_MENU,
    ADMIN_PANEL_BROADCAST_MESSAGE,
) = range(7)

CHANNEL_INVITE_LINK: str = ""
CHANNEL_CHAT_IDENTIFIER: Optional[Union[int, str]] = None
MEMBERSHIP_VERIFY_CALLBACK = "verify_membership"
BROADCAST_OPTIONS = {
    "broadcast:all": {"label": "همه کاربران", "filter": None},
    "broadcast:with_phone": {"label": "کاربران دارای شماره", "filter": True},
    "broadcast:without_phone": {"label": "کاربران بدون شماره", "filter": False},
}

CORE_MENU_BUTTONS = [
    "Case Studies",
    "وبینار ها",
    "دراپ لرنینگ",
    "مشاوره رایگان",
]

SERVICE_BUTTONS = [
    "طراحی سایت",
    "تولید محتوا",
    "مشاوره فروش و بازاریابی",
    "کمپین فروش",
    "تیم سازی و منابع انسانی",
    "برندینگ",
]

REQUEST_CONTACT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("ارسال شماره موبایل", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="لطفاً شماره موبایل خود را ارسال کنید",
)


def membership_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔗 عضویت در کانال", url=CHANNEL_INVITE_LINK)],
            [
                InlineKeyboardButton(
                    "✅ تایید عضویت", callback_data=MEMBERSHIP_VERIFY_CALLBACK
                )
            ],
        ]
    )


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("تنظیمات ربات ⚙️", callback_data="panel:settings")],
            [InlineKeyboardButton("آمار گیری 📊", callback_data="panel:stats")],
            [InlineKeyboardButton("بازگشت به ربات ⬅️", callback_data="panel:back")],
        ]
    )


def admin_settings_keyboard(require_phone: bool) -> InlineKeyboardMarkup:
    toggle_label = (
        "اجبار شماره موبایل: روشن ✅"
        if require_phone
        else "اجبار شماره موبایل: خاموش ❌"
    )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "مدیریت ادمین‌ها 🧑‍💼", callback_data="settings:manage"
                )
            ],
            [InlineKeyboardButton(toggle_label, callback_data="settings:toggle_phone")],
            [InlineKeyboardButton("پیام همگانی 📢", callback_data="settings:broadcast")],
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


def admin_broadcast_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ارسال به همه کاربران", callback_data="broadcast:all")],
            [
                InlineKeyboardButton(
                    "ارسال به کاربران دارای شماره",
                    callback_data="broadcast:with_phone",
                )
            ],
            [
                InlineKeyboardButton(
                    "ارسال به کاربران بدون شماره",
                    callback_data="broadcast:without_phone",
                )
            ],
            [InlineKeyboardButton("بازگشت 🔙", callback_data="broadcast:back")],
        ]
    )


def admin_broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("لغو ارسال 🔙", callback_data="broadcast:cancel")]]
    )

USER_MENU_RESPONSES = {
    "Case Studies": "بخش Case Studies به زودی در دسترس قرار می‌گیرد.",
    "وبینار ها": "وبینارهای جدید به زودی اعلام می‌شوند.",
    "دراپ لرنینگ": "دراپ لرنینگ به زودی فعال می‌شود.",
    "مشاوره رایگان": "مشاوران ما به زودی پاسخگوی شما خواهند بود.",
    "طراحی سایت": "خدمت طراحی سایت به زودی در دسترس قرار می‌گیرد.",
    "تولید محتوا": "خدمت تولید محتوا به زودی در دسترس قرار می‌گیرد.",
    "مشاوره فروش و بازاریابی": "خدمت مشاوره فروش و بازاریابی به زودی در دسترس قرار می‌گیرد.",
    "کمپین فروش": "خدمت کمپین فروش به زودی در دسترس قرار می‌گیرد.",
    "تیم سازی و منابع انسانی": "خدمت تیم سازی و منابع انسانی به زودی در دسترس قرار می‌گیرد.",
    "برندینگ": "خدمت برندینگ به زودی در دسترس قرار می‌گیرد.",
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


def _parse_chat_identifier(raw: Optional[str]) -> Union[int, str]:
    if raw is None:
        raise RuntimeError(
            "CHANNEL_CHAT_ID is required when CHANNEL_ID is an invite link or does not start with @."
        )

    value = raw.strip()
    if not value:
        raise RuntimeError("CHANNEL_CHAT_ID cannot be empty.")

    if value.startswith("@"):
        return value

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            "CHANNEL_CHAT_ID must be a numeric chat ID or start with @ for public channels."
        ) from exc


def load_channel_configuration() -> Tuple[str, Union[int, str]]:
    raw = os.getenv("CHANNEL_ID")
    if not raw:
        raise RuntimeError(
            "CHANNEL_ID is missing. Provide the invite link, @username, or numeric chat ID in the .env file."
        )

    raw_value = raw.strip()
    invite_link = os.getenv("CHANNEL_INVITE_LINK", "").strip()
    chat_identifier_raw: Optional[str] = None

    if raw_value.startswith("http://") or raw_value.startswith("https://"):
        invite_link = raw_value
        chat_identifier_raw = os.getenv("CHANNEL_CHAT_ID")
    else:
        chat_identifier_raw = raw_value
        if not invite_link:
            if raw_value.startswith("@"):
                invite_link = f"https://t.me/{raw_value.lstrip('@')}"
            else:
                if raw_value.startswith("https://t.me/") or raw_value.startswith(
                    "http://t.me/"
                ):
                    invite_link = raw_value
                elif raw_value.startswith("t.me/"):
                    invite_link = f"https://{raw_value}"
                else:
                    raise RuntimeError(
                        "CHANNEL_INVITE_LINK is missing. Provide the channel invite link via CHANNEL_INVITE_LINK when CHANNEL_ID is a numeric ID."
                    )

    if not invite_link:
        raise RuntimeError(
            "CHANNEL_INVITE_LINK is missing. Provide the channel invite link via CHANNEL_ID or CHANNEL_INVITE_LINK."
        )

    chat_identifier = _parse_chat_identifier(chat_identifier_raw)
    return invite_link, chat_identifier


def is_admin_user(telegram_id: int) -> bool:
    return telegram_id in TEMP_ADMIN_IDS or database.is_admin(telegram_id)


def ensure_user_record(update: Update) -> None:
    user = update.effective_user
    if not user:
        return
    database.ensure_user_record(
        telegram_id=user.id,
        fname=user.first_name or "",
        lname=user.last_name or "",
        username=user.username or "",
    )


def phone_requirement_enabled(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.application.bot_data.get("require_phone", False))


def set_phone_requirement(context: ContextTypes.DEFAULT_TYPE, value: bool) -> None:
    context.application.bot_data["require_phone"] = value


async def ensure_private_chat(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    chat = update.effective_chat
    if chat and chat.type != ChatType.PRIVATE:
        if update.message:
            await update.message.reply_text(
                "لطفاً برای استفاده از ربات، گفت‌وگو را به چت خصوصی منتقل کنید."
            )
        elif chat:
            await context.bot.send_message(
                chat_id=chat.id,
                text="این ربات فقط در چت خصوصی پاسخگو است.",
            )
        return False
    return True


async def ensure_registered_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    ensure_user_record(update)
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return False

    if not phone_requirement_enabled(context):
        return True

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


async def is_user_in_channel(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    if CHANNEL_CHAT_IDENTIFIER is None:
        raise RuntimeError(
            "Channel chat identifier is not configured. Ensure CHANNEL_ID (or CHANNEL_CHAT_ID) is set correctly."
        )
    try:
        member = await context.bot.get_chat_member(CHANNEL_CHAT_IDENTIFIER, user_id)
    except TelegramError as exc:
        logging.warning("Failed to fetch chat member %s: %s", user_id, exc)
        return False

    return member.status in {
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.RESTRICTED,
    }


async def prompt_for_channel_membership(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    already_prompted: bool = False,
) -> None:
    message_text = (
        "برای استفاده از ربات، ابتدا باید در کانال خصوصی ما عضو شوید."
        if not already_prompted
        else "به نظر می‌رسد هنوز عضو کانال نشده‌ای. لطفاً پس از عضویت روی «تایید عضویت» بزن."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text, reply_markup=membership_keyboard()
        )
    elif update.message:
        await update.message.reply_text(
            message_text,
            reply_markup=membership_keyboard(),
        )
    else:
        chat = update.effective_chat
        if chat:
            await context.bot.send_message(
                chat_id=chat.id,
                text=message_text,
                reply_markup=membership_keyboard(),
            )


async def ensure_channel_membership(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    ensure_user_record(update)

    user = update.effective_user
    if not user:
        return False

    if await is_user_in_channel(context, user.id):
        return True

    await prompt_for_channel_membership(update, context)
    return False


async def handle_membership_verification(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    ensure_user_record(update)

    user = update.effective_user
    if not user:
        return

    if await is_user_in_channel(context, user.id):
        await query.edit_message_text("عضویت شما تایید شد ✅")
        if phone_requirement_enabled(context) and not database.user_has_phone(user.id):
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="عضویت تایید شد. لطفاً شماره موبایل خود را از طریق دکمه زیر ارسال کنید.",
                reply_markup=REQUEST_CONTACT_KEYBOARD,
            )
        else:
            await send_main_menu(update, context)
    else:
        await prompt_for_channel_membership(
            update, context, already_prompted=True
        )


def build_main_menu_keyboard(user_id: Optional[int]) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(title)] for title in CORE_MENU_BUTTONS]
    rows.extend([[KeyboardButton(title)] for title in SERVICE_BUTTONS])
    if user_id is not None and is_admin_user(user_id):
        rows.append([KeyboardButton("🛠️ پنل ادمین")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def send_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if update.message:
        await update.message.reply_text(
            "سلام! یکی از گزینه‌های زیر را انتخاب کن:",
            reply_markup=build_main_menu_keyboard(user_id),
        )
    else:
        chat = update.effective_chat
        if chat:
            await context.bot.send_message(
                chat_id=chat.id,
                text="سلام! یکی از گزینه‌های زیر را انتخاب کن:",
                reply_markup=build_main_menu_keyboard(user_id),
            )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    if not await ensure_registered_user(update, context):
        return
    await send_main_menu(update, context)


def extract_phone_last10(raw_phone: str) -> Optional[str]:
    digits = "".join(ch for ch in raw_phone if ch.isdigit())
    if len(digits) < 10:
        return None
    return digits[-10:]


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.contact:
        return

    if not await ensure_private_chat(update, context):
        return

    if not await ensure_channel_membership(update, context):
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
    await send_main_menu(update, context)


async def handle_menu_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    if not await ensure_registered_user(update, context):
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
    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

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

    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    data = query.data

    if data == "panel:settings":
        await query.edit_message_text(
            "بخش تنظیمات ربات:",
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        return ADMIN_PANEL_SETTINGS

    if data == "panel:stats":
        stats = database.get_user_stats()
        text = "\n".join(
            [
                "آمار ربات:",
                f"- کل کاربران: {stats['total']}",
                f"- کاربران با شماره موبایل: {stats['with_phone']}",
                f"- کاربران بدون شماره موبایل: {stats['without_phone']}",
            ]
        )
        await query.edit_message_text(text, reply_markup=admin_main_keyboard())
        return ADMIN_PANEL_MAIN

    if data == "panel:back":
        await query.edit_message_text("بازگشت به ربات.")
        await send_main_menu(update, context)
        return ConversationHandler.END

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    return ADMIN_PANEL_MAIN


async def admin_panel_settings_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

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

    if data == "settings:toggle_phone":
        new_state = not phone_requirement_enabled(context)
        set_phone_requirement(context, new_state)
        status_text = (
            "اجبار ارسال شماره موبایل فعال شد ✅"
            if new_state
            else "اجبار ارسال شماره موبایل غیرفعال شد ❌"
        )
        await query.edit_message_text(
            f"{status_text}\n\nیکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_settings_keyboard(new_state),
        )
        return ADMIN_PANEL_SETTINGS

    if data == "settings:broadcast":
        await query.edit_message_text(
            "پیام را برای کدام گروه ارسال می‌کنید؟",
            reply_markup=admin_broadcast_keyboard(),
        )
        return ADMIN_PANEL_BROADCAST_MENU

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

    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

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
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        return ADMIN_PANEL_SETTINGS

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    return ADMIN_PANEL_MANAGE


async def admin_panel_broadcast_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    data = query.data

    if data == "broadcast:back":
        await query.edit_message_text(
            "بخش تنظیمات ربات:",
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        return ADMIN_PANEL_SETTINGS

    option = BROADCAST_OPTIONS.get(data)
    if option is None:
        await query.answer("گزینه نامعتبر است.", show_alert=True)
        return ADMIN_PANEL_BROADCAST_MENU

    context.user_data["broadcast_target"] = data

    await query.edit_message_text(
        f"متن پیام مورد نظر برای «{option['label']}» را ارسال کنید.",
        reply_markup=admin_broadcast_cancel_keyboard(),
    )
    return ADMIN_PANEL_BROADCAST_MESSAGE


async def admin_broadcast_cancel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    context.user_data.pop("broadcast_target", None)

    await query.edit_message_text(
        "ارسال پیام همگانی لغو شد.",
        reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
    )
    return ADMIN_PANEL_SETTINGS


async def admin_broadcast_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    target_key = context.user_data.get("broadcast_target")
    option = BROADCAST_OPTIONS.get(target_key)
    if option is None:
        await update.message.reply_text(
            "حالت ارسال نامعتبر است.",
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        return ADMIN_PANEL_SETTINGS

    message_text = update.message.text
    if not message_text:
        await update.message.reply_text("لطفاً یک پیام متنی ارسال کنید.")
        return ADMIN_PANEL_BROADCAST_MESSAGE

    recipients = list(database.iter_users(has_phone=option["filter"]))

    if not recipients:
        await update.message.reply_text(
            f"هیچ کاربری در گروه «{option['label']}» یافت نشد.",
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        context.user_data.pop("broadcast_target", None)
        return ADMIN_PANEL_SETTINGS

    sent = 0
    failed = 0
    for record in recipients:
        try:
            await context.bot.send_message(
                chat_id=record["telegram_id"],
                text=message_text,
            )
            sent += 1
        except TelegramError as exc:
            logging.warning(
                "Failed to broadcast to %s: %s", record["telegram_id"], exc
            )
            failed += 1

    context.user_data.pop("broadcast_target", None)

    summary_lines = [
        f"پیام برای «{option['label']}» ارسال شد.",
        f"کل مخاطبان: {len(recipients)}",
        f"موفق: {sent}",
        f"ناموفق: {failed}",
    ]
    await update.message.reply_text(
        "\n".join(summary_lines),
        reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
    )
    return ADMIN_PANEL_SETTINGS


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling an update", exc_info=context.error)
    if isinstance(update, Update):
        chat = update.effective_chat
        if chat and chat.type == ChatType.PRIVATE:
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="خطایی رخ داد. لطفاً دوباره تلاش کنید.",
                )
            except TelegramError:
                logging.debug("Failed to send error notification to user %s", chat.id)


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

    def number_to_emoji(n: int) -> str:
        emojis = {
            0: "0️⃣",
            1: "1️⃣",
            2: "2️⃣",
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣",
            6: "6️⃣",
            7: "7️⃣",
            8: "8️⃣",
            9: "9️⃣",
            10: "🔟",
        }
        return emojis.get(n, f"{n}.")

    for idx, record in enumerate(admins, start=1):
        phone_display = record["phone_number"] or "نامشخص"
        full_name = " ".join(
            part for part in (record["fname"], record["lname"]) if part
        ).strip() or "بدون نام"
        username = f"@{record['username']}" if record["username"] else "بدون نام کاربری"
        lines.append(
            "\n".join(
                [
                    number_to_emoji(idx),
                    f"نام: {full_name}",
                    f"یوزرنیم: {username}",
                    f"شماره: {phone_display}",
                ]
            )
        )

    for temp_idx, temp_admin in enumerate(
        sorted(
            tid
            for tid in TEMP_ADMIN_IDS
            if not any(a["telegram_id"] == tid for a in admins)
        ),
        start=len(lines) + 1,
    ):
        lines.append(
            "\n".join(
                [
                    number_to_emoji(temp_idx),
                    "نام: ادمین موقت",
                    "یوزرنیم: نامشخص",
                    f"شماره: نامشخص",
                ]
            )
        )

    if not lines:
        lines.append("ادمینی ثبت نشده است.")

    text = "\n\n".join(lines)

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

    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

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
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
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

    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.edit_message_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

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
        await send_main_menu(update, context)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("خروج از پنل ادمین.")
        await send_main_menu(update, context)
    return ConversationHandler.END


def main() -> None:
    load_env()
    database.init_db()
    token = get_bot_token()
    invite_link, chat_identifier = load_channel_configuration()
    global CHANNEL_INVITE_LINK, CHANNEL_CHAT_IDENTIFIER
    CHANNEL_INVITE_LINK = invite_link
    CHANNEL_CHAT_IDENTIFIER = chat_identifier

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    application = Application.builder().token(token).build()
    require_phone_env = os.getenv("REQUIRE_PHONE_DEFAULT", "").strip().lower()
    phone_required = require_phone_env in {"1", "true", "yes", "on"}
    application.bot_data.setdefault("require_phone", phone_required)

    private_text = filters.ChatType.PRIVATE & filters.TEXT

    admin_panel_handler = ConversationHandler(
        entry_points=[
            CommandHandler("panel", admin_panel_entry, filters=filters.ChatType.PRIVATE),
            MessageHandler(
                private_text & filters.Regex("^🛠️ پنل ادمین$"), admin_panel_entry
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
            ADMIN_PANEL_BROADCAST_MENU: [
                CallbackQueryHandler(
                    admin_panel_broadcast_callback, pattern="^broadcast:"
                ),
            ],
            ADMIN_PANEL_BROADCAST_MESSAGE: [
                MessageHandler(private_text & ~filters.COMMAND, admin_broadcast_message),
                CallbackQueryHandler(
                    admin_broadcast_cancel_callback, pattern="^broadcast:cancel$"
                ),
            ],
            ADMIN_PANEL_ADD_PHONE: [
                MessageHandler(private_text & ~filters.COMMAND, admin_add_phone),
                CallbackQueryHandler(admin_add_cancel_callback, pattern="^add:cancel$"),
            ],
            ADMIN_PANEL_REMOVE_PHONE: [
                CallbackQueryHandler(handle_remove_admin_selection, pattern="^remove:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True,
    )

    application.add_handler(
        CallbackQueryHandler(
            handle_membership_verification,
            pattern=f"^{MEMBERSHIP_VERIFY_CALLBACK}$",
        )
    )
    application.add_handler(
        CommandHandler("start", start, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(admin_panel_handler)
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.CONTACT, handle_contact)
    )
    application.add_handler(
        MessageHandler(private_text & ~filters.COMMAND, handle_menu_selection)
    )

    application.add_error_handler(handle_error)

    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

