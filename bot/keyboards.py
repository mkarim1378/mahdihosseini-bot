"""Keyboard builders used across the bot."""

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from . import config
from .constants import MEMBERSHIP_VERIFY_CALLBACK, SERVICE_BUTTONS

REQUEST_CONTACT_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("ارسال شماره موبایل", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="لطفاً شماره موبایل خود را ارسال کنید",
)


def _chunk_buttons(titles: list[str], row_size: int = 2) -> list[list[KeyboardButton]]:
    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(titles), row_size):
        chunk = [KeyboardButton(title) for title in titles[i : i + row_size]]
        rows.append(chunk)
    return rows


SERVICE_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=_chunk_buttons(SERVICE_BUTTONS, row_size=2)
    + [[KeyboardButton("بازگشت")]],
    resize_keyboard=True,
)


def membership_keyboard() -> InlineKeyboardMarkup:
    invite_url = config.CHANNEL_INVITE_LINK
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔗 عضویت در کانال", url=invite_url)],
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
            [InlineKeyboardButton("مدیریت وبینارها 🎥", callback_data="panel:webinars")],
            [InlineKeyboardButton("بازگشت به ربات ⬅️", callback_data="panel:back")],
        ]
    )


def admin_main_reply_keyboard() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    rows.append(
        [
            KeyboardButton("تنظیمات ربات ⚙️"),
            KeyboardButton("آمار گیری 📊"),
        ]
    )
    rows.append(
        [
            KeyboardButton("مدیریت وبینارها 🎥"),
            KeyboardButton("مدیریت دراپ لرنینگ 📚"),
        ]
    )
    rows.append(
        [
            KeyboardButton("مدیریت کیس استادی 📋"),
            KeyboardButton("بازگشت به ربات ⬅️"),
        ]
    )
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_settings_keyboard(require_phone: bool) -> InlineKeyboardMarkup:
    toggle_label = (
        "اجبار شماره موبایل: روشن ✅" if require_phone else "اجبار شماره موبایل: خاموش ❌"
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


def register_phone_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for requesting phone number registration."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "ثبت نام در ربات", callback_data="register_phone"
                )
            ]
        ]
    )


__all__ = [
    "REQUEST_CONTACT_KEYBOARD",
    "SERVICE_MENU_KEYBOARD",
    "membership_keyboard",
    "admin_main_keyboard",
    "admin_main_reply_keyboard",
    "admin_settings_keyboard",
    "admin_manage_keyboard",
    "admin_add_cancel_keyboard",
    "admin_broadcast_keyboard",
    "admin_broadcast_cancel_keyboard",
    "register_phone_keyboard",
    "ReplyKeyboardRemove",
]


