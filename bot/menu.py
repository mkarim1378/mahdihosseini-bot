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
from .constants import (
    CORE_MENU_BUTTONS,
    CORE_MENU_RESPONSES,
    SERVICE_RESPONSES,
)
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
    consultation_payment_keyboard,
    consultation_receipt_keyboard,
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
    
    # Check if there's a pending item
    pending_webinar_id = context.user_data.get("pending_webinar_id")
    pending_drop_learning_id = context.user_data.get("pending_drop_learning_id")
    pending_case_study_id = context.user_data.get("pending_case_study_id")
    
    if pending_webinar_id:
        context.user_data.pop("pending_webinar_id", None)
        await send_webinar_content(update, context, pending_webinar_id)
    elif pending_drop_learning_id:
        context.user_data.pop("pending_drop_learning_id", None)
        await send_drop_learning_content(update, context, pending_drop_learning_id)
    elif pending_case_study_id:
        context.user_data.pop("pending_case_study_id", None)
        await send_case_study_content(update, context, pending_case_study_id)
    else:
        await send_main_menu(update, context)


async def handle_menu_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    
    # Check registration but don't block if phone requirement is disabled
    # ensure_registered_user will prompt for phone if needed
    registration_ok = await ensure_registered_user(update, context)
    if not registration_ok:
        # ensure_registered_user already sent a message to user, just return
        return

    if not update.message:
        return
        
    user_id = update.effective_user.id if update.effective_user else None
    text = update.message.text or ""
    
    logging.info(f"Handling menu selection: text='{text}', user_id={user_id}")
    
    # Ignore admin panel messages - they should be handled by admin conversation handler
    admin_panel_texts = [
        "تنظیمات ربات ⚙️",
        "آمار گیری 📊",
        "مدیریت وبینارها 🎥",
        "مدیریت دراپ لرنینگ 📚",
        "مدیریت کیس استادی 📋",
        "پیام همگانی 📢",
        "بازگشت به ربات ⬅️",
    ]
    if text in admin_panel_texts:
        return
    if text == "خدمات":
        await update.message.reply_text(
            "یکی از خدمات زیر را انتخاب کن:",
            reply_markup=SERVICE_MENU_KEYBOARD,
        )
        return
    
    if text == "رزرو مشاوره":
        consultation_message = database.get_bot_setting("consultation_message")
        await update.message.reply_text(
            consultation_message,
            reply_markup=consultation_payment_keyboard(),
        )
        return
    
    webinar_map = context.user_data.get("webinar_menu")
    if webinar_map and text in webinar_map:
        webinar_id = webinar_map[text]
        webinar = database.get_webinar(webinar_id)
        if not webinar:
            await update.message.reply_text(
                "این وبینار دیگر در دسترس نیست!",
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
        # Optimized: build menu and map in single pass
        rows: list[list[KeyboardButton]] = []
        menu_map: dict[str, int] = {}
        has_webinars = False
        
        for webinar in database.list_webinars():
            has_webinars = True
            title = webinar["title"] or "وبینار بدون عنوان"
            rows.append([KeyboardButton(title)])
            menu_map[title] = webinar["id"]
        
        if not has_webinars:
            await update.message.reply_text(
                "در حال حاضر وبیناری ثبت نشده است.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            return

        rows.append([KeyboardButton("بازگشت")])
        webinar_keyboard = ReplyKeyboardMarkup(rows, resize_keyboard=True)
        context.user_data["webinar_menu"] = menu_map
        await update.message.reply_text(
            "یکی از وبینارهای زیر را انتخاب کن:",
            reply_markup=webinar_keyboard,
        )
        return

    if text == "دراپ لرنینگ":
        # Optimized: build menu and map in single pass
        rows: list[list[KeyboardButton]] = []
        menu_map: dict[str, int] = {}
        has_items = False
        
        for item in database.list_drop_learning():
            has_items = True
            title = item["title"] or "دراپ لرنینگ بدون عنوان"
            rows.append([KeyboardButton(title)])
            menu_map[title] = item["id"]
        
        if not has_items:
            await update.message.reply_text(
                "در حال حاضر دراپ لرنینگی ثبت نشده است.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            return

        rows.append([KeyboardButton("بازگشت")])
        drop_learning_keyboard = ReplyKeyboardMarkup(rows, resize_keyboard=True)
        context.user_data["drop_learning_menu"] = menu_map
        await update.message.reply_text(
            "یکی از دراپ لرنینگ‌های زیر را انتخاب کن:",
            reply_markup=drop_learning_keyboard,
        )
        return

    if text == "Case Studies":
        # Optimized: build menu and map in single pass
        rows: list[list[KeyboardButton]] = []
        menu_map: dict[str, int] = {}
        has_items = False
        
        for item in database.list_case_studies():
            has_items = True
            title = item["title"] or "کیس استادی بدون عنوان"
            rows.append([KeyboardButton(title)])
            menu_map[title] = item["id"]
        
        if not has_items:
            await update.message.reply_text(
                "در حال حاضر کیس استادی ثبت نشده است.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            return

        rows.append([KeyboardButton("بازگشت")])
        case_studies_keyboard = ReplyKeyboardMarkup(rows, resize_keyboard=True)
        context.user_data["case_studies_menu"] = menu_map
        await update.message.reply_text(
            "یکی از کیس استادی‌های زیر را انتخاب کن:",
            reply_markup=case_studies_keyboard,
        )
        return

    # Handle drop learning selection
    drop_learning_map = context.user_data.get("drop_learning_menu")
    if drop_learning_map and text in drop_learning_map:
        item_id = drop_learning_map[text]
        item = database.get_drop_learning(item_id)
        if not item:
            await update.message.reply_text(
                "این دراپ لرنینگ دیگر در دسترس نیست.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            context.user_data.pop("drop_learning_menu", None)
            return

        user = update.effective_user
        if not user or not database.user_has_phone(user.id):
            context.user_data["pending_drop_learning_id"] = item_id
            await update.message.reply_text(
                "جهت ثبت نام در ربات دکمه رو بزنید",
                reply_markup=register_phone_keyboard(),
            )
            return

        await send_drop_learning_content(update, context, item_id)
        return

    # Handle case studies selection
    case_studies_map = context.user_data.get("case_studies_menu")
    if case_studies_map and text in case_studies_map:
        item_id = case_studies_map[text]
        item = database.get_case_study(item_id)
        if not item:
            await update.message.reply_text(
                "این کیس استادی دیگر در دسترس نیست.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            context.user_data.pop("case_studies_menu", None)
            return

        user = update.effective_user
        if not user or not database.user_has_phone(user.id):
            context.user_data["pending_case_study_id"] = item_id
            await update.message.reply_text(
                "جهت ثبت نام در ربات دکمه رو بزنید",
                reply_markup=register_phone_keyboard(),
            )
            return

        await send_case_study_content(update, context, item_id)
        return

    if text == "بازگشت":
        if context.user_data.pop("webinar_menu", None):
            await update.message.reply_text(
                "بازگشت به منوی اصلی.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            return
        if context.user_data.pop("drop_learning_menu", None):
            await update.message.reply_text(
                "بازگشت به منوی اصلی.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            return
        if context.user_data.pop("case_studies_menu", None):
            await update.message.reply_text(
                "بازگشت به منوی اصلی.",
                reply_markup=build_main_menu_keyboard(user_id),
            )
            return
        await update.message.reply_text(
            "بازگشت به منوی اصلی.",
            reply_markup=build_main_menu_keyboard(user_id),
        )
        return
    elif text in SERVICE_RESPONSES:
        await update.message.reply_text(
            SERVICE_RESPONSES[text],
            reply_markup=SERVICE_MENU_KEYBOARD,
        )
        return
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

    # Record view
    user_id = update.effective_user.id if update.effective_user else None
    if user_id:
        database.record_webinar_view(user_id, webinar_id)

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

    # Send content items - optimized: iterate directly without converting to list
    chat_id = update.effective_chat.id
    for item in database.get_webinar_content(webinar_id):
        try:
            file_type = item["file_type"]
            file_id = item["file_id"]
            
            if file_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=file_id)
            elif file_type == "voice":
                await context.bot.send_voice(chat_id=chat_id, voice=file_id)
            elif file_type == "audio":
                await context.bot.send_audio(chat_id=chat_id, audio=file_id)
            elif file_type == "document":
                await context.bot.send_document(chat_id=chat_id, document=file_id)
            elif file_type == "photo":
                await context.bot.send_photo(chat_id=chat_id, photo=file_id)
            elif file_type == "video_note":
                await context.bot.send_video_note(chat_id=chat_id, video_note=file_id)
        except Exception as e:
            logging.warning(f"Failed to send webinar content {item.get('id', 'unknown')}: {e}")
            continue


async def send_drop_learning_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int
) -> None:
    """Send drop learning content to user."""
    item = database.get_drop_learning(item_id)
    if not item:
        await update.message.reply_text("این دراپ لرنینگ دیگر در دسترس نیست.")
        return

    # Record view
    user_id = update.effective_user.id if update.effective_user else None
    if user_id:
        database.record_drop_learning_view(user_id, item_id)

    # Send description
    await update.message.reply_text(item["description"])

    # Send content items - optimized: iterate directly without converting to list
    chat_id = update.effective_chat.id
    for content_item in database.get_drop_learning_content(item_id):
        try:
            caption = content_item.get("caption") or None
            file_type = content_item["file_type"]
            file_id = content_item["file_id"]
            
            if file_type == "video":
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=caption,
                )
            elif file_type == "voice":
                await context.bot.send_voice(
                    chat_id=chat_id,
                    voice=file_id,
                    caption=caption,
                )
            elif file_type == "audio":
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=file_id,
                    caption=caption,
                )
            elif file_type == "document":
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=file_id,
                    caption=caption,
                )
            elif file_type == "photo":
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption,
                )
            elif file_type == "video_note":
                # video_note doesn't support caption
                await context.bot.send_video_note(
                    chat_id=chat_id,
                    video_note=file_id,
                )
                if caption:
                    await context.bot.send_message(chat_id=chat_id, text=caption)
        except Exception as e:
            logging.warning(f"Failed to send drop learning content {content_item.get('id', 'unknown')}: {e}")
            continue


async def send_case_study_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int
) -> None:
    """Send case study content to user."""
    item = database.get_case_study(item_id)
    if not item:
        await update.message.reply_text("این کیس استادی دیگر در دسترس نیست.")
        return

    # Record view
    user_id = update.effective_user.id if update.effective_user else None
    if user_id:
        database.record_case_study_view(user_id, item_id)

    # Send cover photo if available
    if item.get("cover_photo_file_id"):
        try:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=item["cover_photo_file_id"],
                caption=item["description"],
            )
        except Exception:
            await update.message.reply_text(item["description"])
    else:
        await update.message.reply_text(item["description"])

    # Send content items - optimized: iterate directly without converting to list
    chat_id = update.effective_chat.id
    for content_item in database.get_case_study_content(item_id):
        try:
            file_type = content_item["file_type"]
            file_id = content_item["file_id"]
            
            if file_type == "video":
                await context.bot.send_video(chat_id=chat_id, video=file_id)
            elif file_type == "voice":
                await context.bot.send_voice(chat_id=chat_id, voice=file_id)
            elif file_type == "audio":
                await context.bot.send_audio(chat_id=chat_id, audio=file_id)
            elif file_type == "document":
                await context.bot.send_document(chat_id=chat_id, document=file_id)
            elif file_type == "photo":
                await context.bot.send_photo(chat_id=chat_id, photo=file_id)
            elif file_type == "video_note":
                await context.bot.send_video_note(chat_id=chat_id, video_note=file_id)
        except Exception as e:
            logging.warning(f"Failed to send case study content {content_item.get('id', 'unknown')}: {e}")
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
        # User already has phone, show pending content if any
        pending_webinar_id = context.user_data.get("pending_webinar_id")
        pending_drop_learning_id = context.user_data.get("pending_drop_learning_id")
        pending_case_study_id = context.user_data.get("pending_case_study_id")
        
        if pending_webinar_id:
            context.user_data.pop("pending_webinar_id", None)
            await query.edit_message_text("شماره شما قبلاً ثبت شده است.")
            await send_webinar_content(update, context, pending_webinar_id)
        elif pending_drop_learning_id:
            context.user_data.pop("pending_drop_learning_id", None)
            await query.edit_message_text("شماره شما قبلاً ثبت شده است.")
            await send_drop_learning_content(update, context, pending_drop_learning_id)
        elif pending_case_study_id:
            context.user_data.pop("pending_case_study_id", None)
            await query.edit_message_text("شماره شما قبلاً ثبت شده است.")
            await send_case_study_content(update, context, pending_case_study_id)
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


async def handle_sendphone_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /sendphone command to request phone number."""
    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    
    user = update.effective_user
    if not user:
        return
    
    # Check if user already has phone
    if database.user_has_phone(user.id):
        await update.message.reply_text(
            "شماره موبایل شما قبلاً ثبت شده است.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    
    # Request phone number
    await update.message.reply_text(
        "لطفاً شماره موبایل خود را از طریق دکمه زیر ارسال کنید.",
        reply_markup=REQUEST_CONTACT_KEYBOARD,
    )


async def handle_consultation_payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle consultation payment button click."""
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    if not await ensure_registered_user(update, context):
        return

    payment_amount = database.get_bot_setting("payment_amount")
    payment_card_number = database.get_bot_setting("payment_card_number")
    
    payment_message = f"""💳 اطلاعات پرداخت:

مبلغ: {payment_amount} تومان
شماره کارت: {payment_card_number}

فیش واریز رو باید ارسال کنید از طریق دکمه زیر"""

    await query.edit_message_text(
        payment_message,
        reply_markup=consultation_receipt_keyboard(),
    )


async def handle_consultation_send_receipt_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle send receipt button click."""
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    if not await ensure_registered_user(update, context):
        return

    context.user_data["waiting_for_receipt"] = True
    await query.edit_message_text("لطفاً عکس رسید واریز را ارسال کنید.")


async def handle_receipt_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle receipt photo upload."""
    if not await ensure_private_chat(update, context):
        return
    if not await ensure_channel_membership(update, context):
        return
    if not await ensure_registered_user(update, context):
        return

    if not context.user_data.get("waiting_for_receipt"):
        return

    if not update.message or not update.message.photo:
        await update.message.reply_text("لطفاً یک عکس ارسال کنید.")
        return

    user = update.effective_user
    if not user:
        return

    # Get the largest photo
    photo = update.message.photo[-1]
    receipt_file_id = photo.file_id

    # Create consultation request
    request_id = database.create_consultation_request(user.id, receipt_file_id)
    context.user_data.pop("waiting_for_receipt", None)

    # Get user info
    user_info = database.get_user(user.id)
    user_info_text = f"""کاربر: {user_info['fname']} {user_info['lname']}
شماره موبایل: {user_info['phone_number']}
یوزرنیم: @{user_info['username']}""" if user_info else f"کاربر ID: {user.id}"

    # Send to all admins
    from .utils import is_admin_user
    from .keyboards import consultation_approval_keyboard

    admins = list(database.list_admins())
    for admin in admins:
        try:
            await context.bot.send_photo(
                chat_id=admin["telegram_id"],
                photo=receipt_file_id,
                caption=f"درخواست مشاوره جدید\n\n{user_info_text}",
                reply_markup=consultation_approval_keyboard(request_id),
            )
        except Exception as e:
            logging.warning(f"Failed to send receipt to admin {admin['telegram_id']}: {e}")

    await update.message.reply_text(
        "رسید واریز شما دریافت شد. پس از بررسی، با شما تماس گرفته خواهد شد.",
        reply_markup=build_main_menu_keyboard(user.id),
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
    "handle_consultation_payment_callback",
    "handle_consultation_send_receipt_callback",
    "handle_receipt_photo",
    "handle_membership_verification",
    "handle_menu_selection",
    "handle_register_phone_callback",
    "handle_sendphone_command",
    "send_main_menu",
    "send_webinar_content",
    "send_drop_learning_content",
    "send_case_study_content",
    "start",
]


