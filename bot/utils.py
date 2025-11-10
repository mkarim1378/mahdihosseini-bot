"""Utility helpers shared across bot handlers."""

from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

import database
from .constants import TEMP_ADMIN_IDS
from .keyboards import REQUEST_CONTACT_KEYBOARD


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


def extract_phone_last10(raw_phone: str) -> Optional[str]:
    digits = "".join(ch for ch in raw_phone if ch.isdigit())
    if len(digits) < 10:
        return None
    return digits[-10:]


def is_admin_user(telegram_id: int) -> bool:
    return telegram_id in TEMP_ADMIN_IDS or database.is_admin(telegram_id)


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


async def prompt_for_contact(update: Update) -> None:
    if update.message:
        await update.message.reply_text(
            "برای استفاده از ربات، لطفاً شماره موبایل خود را از طریق دکمه زیر ارسال کنید.",
            reply_markup=REQUEST_CONTACT_KEYBOARD,
        )


__all__ = [
    "ensure_user_record",
    "phone_requirement_enabled",
    "set_phone_requirement",
    "extract_phone_last10",
    "is_admin_user",
    "notify_admin_status_change",
    "prompt_for_contact",
]


