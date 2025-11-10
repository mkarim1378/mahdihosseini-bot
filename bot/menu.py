"""Handlers for public menu interactions."""

from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes

import database
from .constants import CORE_MENU_BUTTONS, CORE_MENU_RESPONSES, SERVICE_RESPONSES
from .guards import (
    ensure_channel_membership,
    ensure_private_chat,
    ensure_registered_user,
    is_user_in_channel,
    prompt_for_channel_membership,
)
from .keyboards import REQUEST_CONTACT_KEYBOARD, SERVICE_MENU_KEYBOARD, membership_keyboard
from .utils import (
    ensure_user_record,
    extract_phone_last10,
    is_admin_user,
    phone_requirement_enabled,
)


def build_main_menu_keyboard(user_id: int | None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(title)] for title in CORE_MENU_BUTTONS]
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
        if text == "خدمات":
            await update.message.reply_text(
                "یکی از خدمات زیر را انتخاب کن:",
                reply_markup=SERVICE_MENU_KEYBOARD,
            )
        elif text == "بازگشت":
            await update.message.reply_text(
                "بازگشت به منوی اصلی.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
        elif text in SERVICE_RESPONSES:
            await update.message.reply_text(
                SERVICE_RESPONSES[text],
                reply_markup=SERVICE_MENU_KEYBOARD,
            )
        else:
            response = CORE_MENU_RESPONSES.get(
                text, "این بخش به زودی در دسترس قرار می‌گیرد."
            )
            await update.message.reply_text(
                response,
                reply_markup=build_main_menu_keyboard(user_id),
            )


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


__all__ = [
    "build_main_menu_keyboard",
    "handle_contact",
    "handle_membership_verification",
    "handle_menu_selection",
    "send_main_menu",
    "start",
]


