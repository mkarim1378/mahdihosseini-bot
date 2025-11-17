"""Handlers for public menu interactions."""

from __future__ import annotations

import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
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
from .keyboards import (
    REQUEST_CONTACT_KEYBOARD,
    SERVICE_MENU_KEYBOARD,
    membership_keyboard,
    register_phone_keyboard,
)
from .utils import (
    ensure_user_record,
    extract_phone_last10,
    is_admin_user,
    phone_requirement_enabled,
)


def build_main_menu_keyboard(user_id: int | None) -> ReplyKeyboardMarkup:
    titles = list(CORE_MENU_BUTTONS)
    if user_id is not None and is_admin_user(user_id):
        titles.append("🛠️ پنل ادمین")

    rows: list[list[KeyboardButton]] = []
    for i in range(0, len(titles), 2):
        chunk = [KeyboardButton(t) for t in titles[i : i + 2]]
        rows.append(chunk)

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
    
    # Check if there's a pending webinar
    pending_webinar_id = context.user_data.get("pending_webinar_id")
    if pending_webinar_id:
        context.user_data.pop("pending_webinar_id", None)
        await send_webinar_content(update, context, pending_webinar_id)
    else:
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
        webinar_map = context.user_data.get("webinar_menu")
        if webinar_map and text in webinar_map:
            webinar_id = webinar_map[text]
            webinar = database.get_webinar(webinar_id)
            if not webinar:
                await update.message.reply_text(
                    "این وبینار دیگر در دسترس نیست.",
                    reply_markup=build_main_menu_keyboard(user_id),
                )
                context.user_data.pop("webinar_menu", None)
                return

            # Check if user has phone number
            user = update.effective_user
            if not user or not database.user_has_phone(user.id):
                # User doesn't have phone, show registration message
                context.user_data["pending_webinar_id"] = webinar_id
                await update.message.reply_text(
                    "جهت ثبت نام در ربات دکمه رو بزنید",
                    reply_markup=register_phone_keyboard(),
                )
                return

            # User has phone, show webinar content
            await send_webinar_content(update, context, webinar_id)
            return

        if text == "وبینار ها":
            webinars = list(database.list_webinars())
            if not webinars:
                await update.message.reply_text(
                    "در حال حاضر وبیناری ثبت نشده است.",
                    reply_markup=build_main_menu_keyboard(user_id),
                )
                return

            titles = [webinar["title"] or "وبینار بدون عنوان" for webinar in webinars]
            rows: list[list[KeyboardButton]] = []
            for i in range(0, len(titles), 2):
                chunk = [KeyboardButton(t) for t in titles[i : i + 2]]
                rows.append(chunk)
            rows.append([KeyboardButton("بازگشت")])

            webinar_keyboard = ReplyKeyboardMarkup(rows, resize_keyboard=True)
            context.user_data["webinar_menu"] = {
                (webinar["title"] or "وبینار بدون عنوان"): webinar["id"]
                for webinar in webinars
            }
            await update.message.reply_text(
                "یکی از وبینارهای زیر را انتخاب کن:",
                reply_markup=webinar_keyboard,
            )
            return

        if text == "بازگشت":
            if context.user_data.pop("webinar_menu", None):
                await update.message.reply_text(
                    "بازگشت به منوی اصلی.",
                    reply_markup=build_main_menu_keyboard(user_id),
                )
                return
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


async def send_webinar_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE, webinar_id: int
) -> None:
    """Send webinar content to user."""
    webinar = database.get_webinar(webinar_id)
    if not webinar:
        await update.message.reply_text("این وبینار دیگر در دسترس نیست.")
        return

    # Send cover photo if available
    if webinar.get("cover_photo_file_id"):
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=webinar["cover_photo_file_id"],
                caption=webinar["description"],
            )
        except Exception:
            # If photo fails, send description as text
            await update.message.reply_text(webinar["description"])
    else:
        await update.message.reply_text(webinar["description"])

    # Send registration link
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "ثبت‌نام در وبینار", url=webinar["registration_link"]
                )
            ]
        ]
    )
    await update.message.reply_text(
        "لینک ثبت‌نام:", reply_markup=keyboard
    )

    # Send content items
    content_items = list(database.get_webinar_content(webinar_id))
    for item in content_items:
        try:
            if item["file_type"] == "video":
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=item["file_id"],
                )
            elif item["file_type"] == "voice":
                await context.bot.send_voice(
                    chat_id=update.effective_chat.id,
                    voice=item["file_id"],
                )
            elif item["file_type"] == "audio":
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=item["file_id"],
                )
            elif item["file_type"] == "document":
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=item["file_id"],
                )
            elif item["file_type"] == "photo":
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=item["file_id"],
                )
            elif item["file_type"] == "video_note":
                await context.bot.send_video_note(
                    chat_id=update.effective_chat.id,
                    video_note=item["file_id"],
                )
        except Exception as e:
            logging.warning(f"Failed to send webinar content {item['id']}: {e}")
            continue


async def handle_register_phone_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle register phone button callback."""
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return

    user = update.effective_user
    if not user:
        return

    # Check if user already has phone
    if database.user_has_phone(user.id):
        # User already has phone, show webinar if pending
        pending_webinar_id = context.user_data.get("pending_webinar_id")
        if pending_webinar_id:
            context.user_data.pop("pending_webinar_id", None)
            await query.edit_message_text("شماره شما قبلاً ثبت شده است.")
            await send_webinar_content(update, context, pending_webinar_id)
        else:
            await query.edit_message_text("شماره شما قبلاً ثبت شده است.")
        return

    # Request phone number
    await query.edit_message_text(
        "لطفاً شماره موبایل خود را از طریق دکمه زیر ارسال کنید.",
    )
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="شماره موبایل خود را ارسال کنید:",
        reply_markup=REQUEST_CONTACT_KEYBOARD,
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
    "handle_register_phone_callback",
    "send_main_menu",
    "send_webinar_content",
    "start",
]


