"""Conversation handlers for the admin panel."""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database
from ..constants import (
    ADMIN_PANEL_ADD_PHONE,
    ADMIN_PANEL_BROADCAST_MENU,
    ADMIN_PANEL_BROADCAST_MESSAGE,
    ADMIN_PANEL_MAIN,
    ADMIN_PANEL_MANAGE,
    ADMIN_PANEL_REMOVE_PHONE,
    ADMIN_PANEL_SETTINGS,
    ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION,
    ADMIN_PANEL_WEBINAR_ADD_TITLE,
    ADMIN_PANEL_WEBINAR_ADD_COVER,
    ADMIN_PANEL_WEBINAR_ADD_CONTENT,
    ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION,
    ADMIN_PANEL_WEBINAR_EDIT_TITLE,
    ADMIN_PANEL_WEBINAR_MENU,
    ADMIN_PANEL_DROP_LEARNING_MENU,
    ADMIN_PANEL_DROP_LEARNING_ADD_TITLE,
    ADMIN_PANEL_DROP_LEARNING_ADD_DESCRIPTION,
    ADMIN_PANEL_DROP_LEARNING_ADD_COVER,
    ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT,
    ADMIN_PANEL_DROP_LEARNING_EDIT_TITLE,
    ADMIN_PANEL_DROP_LEARNING_EDIT_DESCRIPTION,
    ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT,
    ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT_ITEM,
    ADMIN_PANEL_DROP_LEARNING_EDIT_CONTENT_ITEM,
    ADMIN_PANEL_CASE_STUDIES_MENU,
    ADMIN_PANEL_CASE_STUDIES_ADD_TITLE,
    ADMIN_PANEL_CASE_STUDIES_ADD_DESCRIPTION,
    ADMIN_PANEL_CASE_STUDIES_ADD_COVER,
    ADMIN_PANEL_CASE_STUDIES_ADD_CONTENT,
    ADMIN_PANEL_CASE_STUDIES_EDIT_TITLE,
    ADMIN_PANEL_CASE_STUDIES_EDIT_DESCRIPTION,
    BROADCAST_OPTIONS,
    TEMP_ADMIN_IDS,
)
from ..guards import (
    ensure_channel_membership,
    ensure_private_chat,
    ensure_registered_user,
)
from ..keyboards import (
    admin_add_cancel_keyboard,
    admin_broadcast_cancel_keyboard,
    admin_broadcast_keyboard,
    admin_main_keyboard,
    admin_main_reply_keyboard,
    admin_manage_keyboard,
    admin_settings_keyboard,
)
from ..menu import send_main_menu
from ..utils import (
    extract_phone_last10,
    is_admin_user,
    notify_admin_status_change,
    phone_requirement_enabled,
    set_phone_requirement,
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
        await query.edit_message_text("به پنل ادمین خوش آمدید.")
        await query.message.reply_text(
            "یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
        )
    elif update.message:
        await update.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
        )
    return ADMIN_PANEL_MAIN


async def admin_panel_main_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_private_chat(update, context):
        return ConversationHandler.END
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        if update.message:
            await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    text = (update.message.text or "").strip()

    if text == "تنظیمات ربات ⚙️":
        await update.message.reply_text(
            "بخش تنظیمات ربات:",
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        return ADMIN_PANEL_SETTINGS

    if text == "آمار گیری 📊":
        stats = database.get_user_stats()
        lines = [
            "آمار ربات:",
            "",
            "👥 کاربران:",
            f"- کل کاربران: {stats['total']}",
            f"- کاربران با شماره موبایل: {stats['with_phone']}",
            f"- کاربران بدون شماره موبایل: {stats['without_phone']}",
            "",
            "📊 آمار بخش‌ها:",
            f"- بازدیدکنندگان وبینارها: {stats.get('webinar_viewers', 0)}",
            f"- بازدیدکنندگان دراپ لرنینگ: {stats.get('drop_learning_viewers', 0)}",
            f"- بازدیدکنندگان کیس استادی: {stats.get('case_studies_viewers', 0)}",
        ]
        await update.message.reply_text("\n".join(lines))
        return ADMIN_PANEL_MAIN

    if text == "مدیریت وبینارها 🎥":
        await show_webinar_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_WEBINAR_MENU

    if text == "مدیریت دراپ لرنینگ 📚":
        await show_drop_learning_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_DROP_LEARNING_MENU

    if text == "مدیریت کیس استادی 📋":
        await show_case_studies_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_CASE_STUDIES_MENU

    if text == "پیام همگانی 📢":
        await update.message.reply_text(
            "پیام را برای کدام گروه ارسال می‌کنید؟",
            reply_markup=admin_broadcast_keyboard(),
        )
        return ADMIN_PANEL_BROADCAST_MENU

    if text == "بازگشت به ربات ⬅️":
        await update.message.reply_text("بازگشت به ربات.")
        await send_main_menu(update, context)
        return ConversationHandler.END

    await update.message.reply_text("گزینه نامعتبر است. لطفاً یکی از گزینه‌های منو را انتخاب کنید.")
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
                "",
                "👥 کاربران:",
                f"- کل کاربران: {stats['total']}",
                f"- کاربران با شماره موبایل: {stats['with_phone']}",
                f"- کاربران بدون شماره موبایل: {stats['without_phone']}",
                "",
                "📊 آمار بخش‌ها:",
                f"- بازدیدکنندگان وبینارها: {stats.get('webinar_viewers', 0)}",
                f"- بازدیدکنندگان دراپ لرنینگ: {stats.get('drop_learning_viewers', 0)}",
                f"- بازدیدکنندگان کیس استادی: {stats.get('case_studies_viewers', 0)}",
            ]
        )
        await query.edit_message_text(text)
        await query.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
        )
        return ADMIN_PANEL_MAIN

    if data == "panel:webinars":
        await show_webinar_menu(query, context)
        return ADMIN_PANEL_WEBINAR_MENU

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
        admin_list_text = format_admin_list_text()
        message_text = "بخش مدیریت ادمین‌ها:\n\n📋 لیست ادمین‌ها:\n" + admin_list_text
        await query.edit_message_text(
            message_text,
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

    if data == "settings:back":
        await query.edit_message_text("بازگشت به پنل ادمین.")
        await query.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
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


WEBINAR_CANCEL_MARKUP = InlineKeyboardMarkup(
    [[InlineKeyboardButton("انصراف 🔙", callback_data="webinar:menu")]]
)

WEBINAR_CONTENT_MARKUP = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("پایان ✅", callback_data="webinar:finish")],
        [InlineKeyboardButton("انصراف 🔙", callback_data="webinar:menu")],
    ]
)


def _webinar_preview_label(description: str) -> str:
    first_line = (description or "").strip().splitlines()[0] if description else ""
    if not first_line:
        first_line = "وبینار بدون عنوان"
    if len(first_line) > 40:
        return f"{first_line[:37]}..."
    return first_line


def _looks_like_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


async def show_webinar_menu(
    target, context: ContextTypes.DEFAULT_TYPE, status: str | None = None
) -> None:
    webinars = list(database.list_webinars())
    keyboard = [
        [InlineKeyboardButton("➕ افزودن وبینار", callback_data="webinar:add")]
    ]
    for webinar in webinars:
        keyboard.append(
            [
                InlineKeyboardButton(
                    (webinar["title"] or "").strip()
                    or _webinar_preview_label(webinar["description"]),
                    callback_data=f"webinar:select:{webinar['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="webinar:back")])

    text = "مدیریت وبینارها:"
    if status:
        text += f"\n\n{status}"
    if not webinars:
        text += "\n\nوبیناری ثبت نشده است."

    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(target, "edit_message_text"):
        try:
            await target.edit_message_text(text, reply_markup=markup)
        except Exception:
            # If edit fails, send new message
            await context.bot.send_message(chat_id=target.message.chat_id, text=text, reply_markup=markup)
    else:
        await context.bot.send_message(chat_id=target, text=text, reply_markup=markup)


async def show_selected_webinar(
    query, webinar: dict[str, str], status: str | None = None
) -> None:
    text_parts = []
    if status:
        text_parts.append(status)
        text_parts.append("")
    text_parts.append("مشخصات وبینار انتخاب‌شده:")
    text_parts.append("")
    text_parts.append(f"عنوان: {webinar['title'] or 'وبینار بدون عنوان'}")
    text_parts.append("")
    text_parts.append(webinar["description"])
    text = "\n".join(text_parts)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ویرایش عنوان 🏷️", callback_data="webinar:edit_title")],
            [InlineKeyboardButton("ویرایش توضیحات 📝", callback_data="webinar:edit_desc")],
            [InlineKeyboardButton("حذف وبینار 🗑️", callback_data="webinar:delete")],
            [InlineKeyboardButton("بازگشت 🔙", callback_data="webinar:menu")],
        ]
    )
    await query.edit_message_text(text, reply_markup=keyboard)


async def admin_panel_webinar_callback(
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

    if data == "webinar:back":
        context.user_data.pop("webinar_flow", None)
        context.user_data.pop("webinar_selected", None)
        await query.edit_message_text("بازگشت به پنل ادمین.")
        await query.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
        )
        return ADMIN_PANEL_MAIN

    if data == "webinar:menu":
        context.user_data.pop("webinar_flow", None)
        await show_webinar_menu(query, context)
        return ADMIN_PANEL_WEBINAR_MENU

    if data == "webinar:add":
        context.user_data["webinar_flow"] = {"content_items": []}
        await query.edit_message_text(
            "عنوان وبینار را ارسال کنید.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_TITLE

    if data.startswith("webinar:select:"):
        try:
            webinar_id = int(data.split(":", maxsplit=2)[2])
        except (IndexError, ValueError):
            await query.answer("گزینه نامعتبر است.", show_alert=True)
            await show_webinar_menu(query, context)
            return ADMIN_PANEL_WEBINAR_MENU

        webinar = database.get_webinar(webinar_id)
        if webinar is None:
            await query.answer("این وبینار وجود ندارد.", show_alert=True)
            await show_webinar_menu(query, context)
            return ADMIN_PANEL_WEBINAR_MENU

        context.user_data["webinar_selected"] = webinar_id
        await show_selected_webinar(query, webinar)
        return ADMIN_PANEL_WEBINAR_MENU

    if data == "webinar:edit_title":
        webinar_id = context.user_data.get("webinar_selected")
        if not webinar_id:
            await query.answer("ابتدا وبینار را انتخاب کنید.", show_alert=True)
            await show_webinar_menu(query, context)
            return ADMIN_PANEL_WEBINAR_MENU
        context.user_data["webinar_flow"] = {"webinar_id": webinar_id}
        await query.edit_message_text(
            "عنوان جدید وبینار را ارسال کنید.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_EDIT_TITLE

    if data == "webinar:edit_desc":
        webinar_id = context.user_data.get("webinar_selected")
        if not webinar_id:
            await query.answer("ابتدا وبینار را انتخاب کنید.", show_alert=True)
            await show_webinar_menu(query, context)
            return ADMIN_PANEL_WEBINAR_MENU
        context.user_data["webinar_flow"] = {"webinar_id": webinar_id}
        await query.edit_message_text(
            "توضیحات جدید وبینار را ارسال کنید.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION


    if data == "webinar:delete":
        webinar_id = context.user_data.get("webinar_selected")
        if not webinar_id:
            await query.answer("ابتدا وبینار را انتخاب کنید.", show_alert=True)
            await show_webinar_menu(query, context)
            return ADMIN_PANEL_WEBINAR_MENU
        context.user_data.pop("webinar_flow", None)
        if database.delete_webinar(webinar_id):
            context.user_data.pop("webinar_selected", None)
            await show_webinar_menu(query, context, status="وبینار حذف شد ✅")
        else:
            await show_webinar_menu(
                query, context, status="حذف وبینار با خطا مواجه شد."
            )
        return ADMIN_PANEL_WEBINAR_MENU

    if data == "webinar:finish":
        flow = context.user_data.get("webinar_flow") or {}
        title = flow.get("title")
        description = flow.get("description")
        cover_photo_file_id = flow.get("cover_photo_file_id")
        content_items = flow.get("content_items", [])
        
        if not title or not description:
            await query.answer("اطلاعات وبینار ناقص است.", show_alert=True)
            return ADMIN_PANEL_WEBINAR_ADD_CONTENT
        
        # Create webinar
        webinar_id = database.create_webinar(
            title, description, cover_photo_file_id
        )
        
        # Add content items
        for item in content_items:
            database.add_webinar_content(
                webinar_id, item["file_id"], item["file_type"], item["order"]
            )
        
        context.user_data.pop("webinar_flow", None)
        await query.answer("وبینار با موفقیت ثبت شد ✅", show_alert=False)
        # Edit the current message to show menu
        webinars = list(database.list_webinars())
        keyboard = [
            [InlineKeyboardButton("➕ افزودن وبینار", callback_data="webinar:add")]
        ]
        for webinar in webinars:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        (webinar["title"] or "").strip()
                        or _webinar_preview_label(webinar["description"]),
                        callback_data=f"webinar:select:{webinar['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="webinar:back")])
        text = "مدیریت وبینارها:\n\nوبینار جدید ثبت شد ✅"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ADMIN_PANEL_WEBINAR_MENU

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    await show_webinar_menu(query, context)
    return ADMIN_PANEL_WEBINAR_MENU


async def admin_panel_drop_learning_callback(
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

    if data == "drop_learning:back":
        context.user_data.pop("drop_learning_flow", None)
        context.user_data.pop("drop_learning_selected", None)
        await query.edit_message_text("بازگشت به پنل ادمین.")
        await query.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
        )
        return ADMIN_PANEL_MAIN

    if data == "drop_learning:menu":
        context.user_data.pop("drop_learning_flow", None)
        # Reset selected item when going back to menu
        context.user_data.pop("drop_learning_selected", None)
        await show_drop_learning_menu(query, context)
        return ADMIN_PANEL_DROP_LEARNING_MENU

    if data == "drop_learning:add":
        context.user_data["drop_learning_flow"] = {"content_items": []}
        await query.edit_message_text(
            "عنوان دراپ لرنینگ را ارسال کنید.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_ADD_TITLE

    if data.startswith("drop_learning:select:"):
        try:
            item_id = int(data.split(":", maxsplit=2)[2])
        except (IndexError, ValueError):
            await query.answer("گزینه نامعتبر است.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU

        item = database.get_drop_learning(item_id)
        if item is None:
            await query.answer("این دراپ لرنینگ وجود ندارد.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU

        context.user_data["drop_learning_selected"] = item_id
        await show_selected_drop_learning(query, item)
        return ADMIN_PANEL_DROP_LEARNING_MENU

    if data == "drop_learning:edit_title":
        item_id = context.user_data.get("drop_learning_selected")
        if not item_id:
            await query.answer("ابتدا دراپ لرنینگ را انتخاب کنید.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU
        context.user_data["drop_learning_flow"] = {"item_id": item_id}
        await query.edit_message_text(
            "عنوان جدید دراپ لرنینگ را ارسال کنید.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_EDIT_TITLE

    if data == "drop_learning:edit_desc":
        item_id = context.user_data.get("drop_learning_selected")
        if not item_id:
            await query.answer("ابتدا دراپ لرنینگ را انتخاب کنید.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU
        context.user_data["drop_learning_flow"] = {"item_id": item_id}
        await query.edit_message_text(
            "توضیحات جدید دراپ لرنینگ را ارسال کنید.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_EDIT_DESCRIPTION

    if data == "drop_learning:manage_content":
        item_id = context.user_data.get("drop_learning_selected")
        if not item_id:
            await query.answer("ابتدا دراپ لرنینگ را انتخاب کنید.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU
        await show_drop_learning_content_list(query, context, item_id)
        return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT

    if data == "drop_learning:delete":
        item_id = context.user_data.get("drop_learning_selected")
        if not item_id:
            await query.answer("ابتدا دراپ لرنینگ را انتخاب کنید.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU
        context.user_data.pop("drop_learning_flow", None)
        if database.delete_drop_learning(item_id):
            context.user_data.pop("drop_learning_selected", None)
            await show_drop_learning_menu(query, context, status="دراپ لرنینگ حذف شد ✅")
        else:
            await show_drop_learning_menu(
                query, context, status="حذف دراپ لرنینگ با خطا مواجه شد."
            )
        return ADMIN_PANEL_DROP_LEARNING_MENU

    if data.startswith("drop_learning:content:add"):
        item_id = context.user_data.get("drop_learning_selected")
        if not item_id:
            await query.answer("ابتدا دراپ لرنینگ را انتخاب کنید.", show_alert=True)
            await show_drop_learning_menu(query, context)
            return ADMIN_PANEL_DROP_LEARNING_MENU
        context.user_data["drop_learning_flow"] = {"item_id": item_id, "mode": "add_content"}
        await query.edit_message_text(
            "محتوای جدید را ارسال کنید (ویدیو، وویس، فایل و...).",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT_ITEM

    if data.startswith("drop_learning:content:edit:"):
        try:
            content_id = int(data.split(":", maxsplit=3)[3])
        except (IndexError, ValueError):
            await query.answer("گزینه نامعتبر است.", show_alert=True)
            return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT
        
        content_item = database.get_drop_learning_content_item(content_id)
        if not content_item:
            await query.answer("این محتوا وجود ندارد.", show_alert=True)
            item_id = context.user_data.get("drop_learning_selected")
            if item_id:
                await show_drop_learning_content_list(query, context, item_id)
            return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT
        
        context.user_data["drop_learning_flow"] = {
            "item_id": content_item["drop_learning_id"],
            "content_id": content_id,
            "mode": "edit_content"
        }
        await query.edit_message_text(
            "محتوای جدید را برای جایگزینی ارسال کنید (ویدیو، وویس، فایل و...).",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_EDIT_CONTENT_ITEM

    if data.startswith("drop_learning:content:delete:"):
        try:
            content_id = int(data.split(":", maxsplit=3)[3])
        except (IndexError, ValueError):
            await query.answer("گزینه نامعتبر است.", show_alert=True)
            return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT
        
        item_id = context.user_data.get("drop_learning_selected")
        if database.delete_drop_learning_content(content_id):
            await query.answer("محتوا حذف شد ✅", show_alert=False)
            if item_id:
                await show_drop_learning_content_list(query, context, item_id)
        else:
            await query.answer("حذف محتوا با خطا مواجه شد.", show_alert=True)
        return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT

    if data == "drop_learning:finish":
        flow = context.user_data.get("drop_learning_flow") or {}
        title = flow.get("title")
        description = flow.get("description")
        content_items = flow.get("content_items", [])
        
        if not title or not description:
            await query.answer("اطلاعات دراپ لرنینگ ناقص است.", show_alert=True)
            return ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT
        
        # Create drop learning
        item_id = database.create_drop_learning(
            title, description
        )
        
        # Add content items
        for item in content_items:
            database.add_drop_learning_content(
                item_id, item["file_id"], item["file_type"], item["order"]
            )
        
        context.user_data.pop("drop_learning_flow", None)
        await query.answer("دراپ لرنینگ با موفقیت ثبت شد ✅", show_alert=False)
        # Edit the current message to show menu
        items = list(database.list_drop_learning())
        keyboard = [
            [InlineKeyboardButton("➕ افزودن دراپ لرنینگ", callback_data="drop_learning:add")]
        ]
        for item in items:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        (item["title"] or "").strip()
                        or _drop_learning_preview_label(item["description"]),
                        callback_data=f"drop_learning:select:{item['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="drop_learning:back")])
        text = "مدیریت دراپ لرنینگ:\n\nدراپ لرنینگ جدید ثبت شد ✅"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ADMIN_PANEL_DROP_LEARNING_MENU

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    await show_drop_learning_menu(query, context)
    return ADMIN_PANEL_DROP_LEARNING_MENU


async def admin_panel_case_studies_callback(
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

    if data == "case_studies:back":
        context.user_data.pop("case_studies_flow", None)
        context.user_data.pop("case_studies_selected", None)
        await query.edit_message_text("بازگشت به پنل ادمین.")
        await query.message.reply_text(
            "به پنل ادمین خوش آمدید. یکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=admin_main_reply_keyboard(),
        )
        return ADMIN_PANEL_MAIN

    if data == "case_studies:menu":
        context.user_data.pop("case_studies_flow", None)
        await show_case_studies_menu(query, context)
        return ADMIN_PANEL_CASE_STUDIES_MENU

    if data == "case_studies:add":
        context.user_data["case_studies_flow"] = {"content_items": []}
        await query.edit_message_text(
            "عنوان کیس استادی را ارسال کنید.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_ADD_TITLE

    if data.startswith("case_studies:select:"):
        try:
            item_id = int(data.split(":", maxsplit=2)[2])
        except (IndexError, ValueError):
            await query.answer("گزینه نامعتبر است.", show_alert=True)
            await show_case_studies_menu(query, context)
            return ADMIN_PANEL_CASE_STUDIES_MENU

        item = database.get_case_study(item_id)
        if item is None:
            await query.answer("این کیس استادی وجود ندارد.", show_alert=True)
            await show_case_studies_menu(query, context)
            return ADMIN_PANEL_CASE_STUDIES_MENU

        context.user_data["case_studies_selected"] = item_id
        await show_selected_case_study(query, item)
        return ADMIN_PANEL_CASE_STUDIES_MENU

    if data == "case_studies:edit_title":
        item_id = context.user_data.get("case_studies_selected")
        if not item_id:
            await query.answer("ابتدا کیس استادی را انتخاب کنید.", show_alert=True)
            await show_case_studies_menu(query, context)
            return ADMIN_PANEL_CASE_STUDIES_MENU
        context.user_data["case_studies_flow"] = {"item_id": item_id}
        await query.edit_message_text(
            "عنوان جدید کیس استادی را ارسال کنید.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_EDIT_TITLE

    if data == "case_studies:edit_desc":
        item_id = context.user_data.get("case_studies_selected")
        if not item_id:
            await query.answer("ابتدا کیس استادی را انتخاب کنید.", show_alert=True)
            await show_case_studies_menu(query, context)
            return ADMIN_PANEL_CASE_STUDIES_MENU
        context.user_data["case_studies_flow"] = {"item_id": item_id}
        await query.edit_message_text(
            "توضیحات جدید کیس استادی را ارسال کنید.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_EDIT_DESCRIPTION

    if data == "case_studies:delete":
        item_id = context.user_data.get("case_studies_selected")
        if not item_id:
            await query.answer("ابتدا کیس استادی را انتخاب کنید.", show_alert=True)
            await show_case_studies_menu(query, context)
            return ADMIN_PANEL_CASE_STUDIES_MENU
        context.user_data.pop("case_studies_flow", None)
        if database.delete_case_study(item_id):
            context.user_data.pop("case_studies_selected", None)
            await show_case_studies_menu(query, context, status="کیس استادی حذف شد ✅")
        else:
            await show_case_studies_menu(
                query, context, status="حذف کیس استادی با خطا مواجه شد."
            )
        return ADMIN_PANEL_CASE_STUDIES_MENU

    if data == "case_studies:finish":
        flow = context.user_data.get("case_studies_flow") or {}
        title = flow.get("title")
        description = flow.get("description")
        cover_photo_file_id = flow.get("cover_photo_file_id")
        content_items = flow.get("content_items", [])
        
        if not title or not description:
            await query.answer("اطلاعات کیس استادی ناقص است.", show_alert=True)
            return ADMIN_PANEL_CASE_STUDIES_ADD_CONTENT
        
        # Create case study
        item_id = database.create_case_study(
            title, description, cover_photo_file_id
        )
        
        # Add content items
        for item in content_items:
            database.add_case_study_content(
                item_id, item["file_id"], item["file_type"], item["order"]
            )
        
        context.user_data.pop("case_studies_flow", None)
        await query.answer("کیس استادی با موفقیت ثبت شد ✅", show_alert=False)
        # Edit the current message to show menu
        items = list(database.list_case_studies())
        keyboard = [
            [InlineKeyboardButton("➕ افزودن کیس استادی", callback_data="case_studies:add")]
        ]
        for item in items:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        (item["title"] or "").strip()
                        or _case_studies_preview_label(item["description"]),
                        callback_data=f"case_studies:select:{item['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="case_studies:back")])
        text = "مدیریت کیس استادی:\n\nکیس استادی جدید ثبت شد ✅"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return ADMIN_PANEL_CASE_STUDIES_MENU

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    await show_case_studies_menu(query, context)
    return ADMIN_PANEL_CASE_STUDIES_MENU


async def admin_webinar_add_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("webinar_flow") or {}
    title = flow.get("title")
    if not title:
        await update.message.reply_text(
            "عنوان وبینار مشخص نیست. لطفاً دوباره شروع کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_TITLE

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات وبینار نمی‌تواند خالی باشد. لطفاً دوباره ارسال کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION

    flow["description"] = description
    context.user_data["webinar_flow"] = flow
    await update.message.reply_text(
        "عکس کاور وبینار را ارسال کنید (یا /skip برای رد کردن).",
        reply_markup=WEBINAR_CANCEL_MARKUP,
    )
    return ADMIN_PANEL_WEBINAR_ADD_COVER




async def admin_webinar_edit_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    webinar_id = context.user_data.get("webinar_selected")
    if not webinar_id:
        await update.message.reply_text("ابتدا وبینار را از فهرست انتخاب کن.")
        await show_webinar_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_WEBINAR_MENU

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات جدید نمی‌تواند خالی باشد. دوباره تلاش کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION

    database.update_webinar(webinar_id, description=description)
    context.user_data.pop("webinar_flow", None)
    await update.message.reply_text("توضیحات وبینار به‌روزرسانی شد ✅")
    await show_webinar_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_WEBINAR_MENU


async def admin_webinar_add_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "عنوان وبینار نمی‌تواند خالی باشد. لطفاً دوباره تلاش کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_TITLE

    flow = context.user_data.get("webinar_flow") or {}
    flow["title"] = title
    context.user_data["webinar_flow"] = flow
    await update.message.reply_text(
        "توضیحات وبینار را ارسال کن.",
        reply_markup=WEBINAR_CANCEL_MARKUP,
    )
    return ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION


async def admin_webinar_add_cover(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("webinar_flow") or {}
    
    # Check if it's a skip command
    if update.message.text and update.message.text.strip() == "/skip":
        flow["cover_photo_file_id"] = None
    elif update.message.photo:
        # Get the largest photo
        photo = update.message.photo[-1]
        flow["cover_photo_file_id"] = photo.file_id
    else:
        await update.message.reply_text(
            "لطفاً یک عکس ارسال کنید یا /skip را بزنید.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_COVER

    context.user_data["webinar_flow"] = flow
    await update.message.reply_text(
        "محتوای وبینار را ارسال کنید (ویدیو، وویس، فایل و...).\n"
        "می‌توانید چندین محتوا ارسال کنید.\n"
        "بعد از اتمام، دکمه «پایان ✅» را بزنید.",
        reply_markup=WEBINAR_CONTENT_MARKUP,
    )
    return ADMIN_PANEL_WEBINAR_ADD_CONTENT


async def admin_webinar_add_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("webinar_flow") or {}
    content_items = flow.get("content_items", [])
    
    file_id = None
    file_type = None
    
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        file_type = "voice"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video_note:
        file_id = update.message.video_note.file_id
        file_type = "video_note"
    
    if file_id and file_type:
        content_items.append({
            "file_id": file_id,
            "file_type": file_type,
            "order": len(content_items)
        })
        flow["content_items"] = content_items
        context.user_data["webinar_flow"] = flow
        await update.message.reply_text(
            f"محتوای {len(content_items)} ثبت شد.\n"
            "می‌توانید محتوای دیگری ارسال کنید یا دکمه «پایان ✅» را بزنید.",
            reply_markup=WEBINAR_CONTENT_MARKUP,
        )
    else:
        await update.message.reply_text(
            "لطفاً یک فایل (ویدیو، وویس، فایل و...) ارسال کنید.",
            reply_markup=WEBINAR_CONTENT_MARKUP,
        )
    
    return ADMIN_PANEL_WEBINAR_ADD_CONTENT


async def admin_webinar_edit_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    webinar_id = context.user_data.get("webinar_selected")
    if not webinar_id:
        await update.message.reply_text("ابتدا وبینار را از فهرست انتخاب کن.")
        await show_webinar_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_WEBINAR_MENU

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "عنوان نمی‌تواند خالی باشد. دوباره ارسال کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_EDIT_TITLE

    database.update_webinar(webinar_id, title=title)
    context.user_data.pop("webinar_flow", None)
    await update.message.reply_text("عنوان وبینار به‌روزرسانی شد ✅")
    await show_webinar_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_WEBINAR_MENU


# Drop Learning message handlers
async def admin_drop_learning_add_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "عنوان دراپ لرنینگ نمی‌تواند خالی باشد.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_ADD_TITLE

    flow = context.user_data.get("drop_learning_flow") or {}
    flow["title"] = title
    context.user_data["drop_learning_flow"] = flow
    await update.message.reply_text(
        "توضیحات دراپ لرنینگ را ارسال کنید.",
        reply_markup=DROP_LEARNING_CANCEL_MARKUP,
    )
    return ADMIN_PANEL_DROP_LEARNING_ADD_DESCRIPTION


async def admin_drop_learning_add_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("drop_learning_flow") or {}
    title = flow.get("title")
    if not title:
        await update.message.reply_text(
            "عنوان دراپ لرنینگ مشخص نیست.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_ADD_TITLE

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات دراپ لرنینگ نمی‌تواند خالی باشد.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_ADD_DESCRIPTION

    flow["description"] = description
    context.user_data["drop_learning_flow"] = flow
    await update.message.reply_text(
        "محتوای دراپ لرنینگ را ارسال کنید (ویدیو، وویس، فایل و...).\n"
        "می‌توانید چندین محتوا ارسال کنید.\n"
        "بعد از اتمام، دکمه «پایان ✅» را بزنید.",
        reply_markup=DROP_LEARNING_CONTENT_MARKUP,
    )
    return ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT


async def admin_drop_learning_add_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("drop_learning_flow") or {}
    content_items = flow.get("content_items", [])
    
    file_id = None
    file_type = None
    
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        file_type = "voice"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video_note:
        file_id = update.message.video_note.file_id
        file_type = "video_note"
    
    if file_id and file_type:
        content_items.append({
            "file_id": file_id,
            "file_type": file_type,
            "order": len(content_items)
        })
        flow["content_items"] = content_items
        context.user_data["drop_learning_flow"] = flow
        await update.message.reply_text(
            f"محتوای {len(content_items)} ثبت شد.\n"
            "می‌توانید محتوای دیگری ارسال کنید یا دکمه «پایان ✅» را بزنید.",
            reply_markup=DROP_LEARNING_CONTENT_MARKUP,
        )
    else:
        await update.message.reply_text(
            "لطفاً یک فایل (ویدیو، وویس، فایل و...) ارسال کنید.",
            reply_markup=DROP_LEARNING_CONTENT_MARKUP,
        )
    
    return ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT


async def admin_drop_learning_edit_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    item_id = context.user_data.get("drop_learning_selected")
    if not item_id:
        await update.message.reply_text("ابتدا دراپ لرنینگ را از فهرست انتخاب کنید.")
        await show_drop_learning_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_DROP_LEARNING_MENU

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات جدید نمی‌تواند خالی باشد.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_EDIT_DESCRIPTION

    database.update_drop_learning(item_id, description=description)
    context.user_data.pop("drop_learning_flow", None)
    await update.message.reply_text("توضیحات دراپ لرنینگ به‌روزرسانی شد ✅")
    await show_drop_learning_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_DROP_LEARNING_MENU


async def admin_drop_learning_edit_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    item_id = context.user_data.get("drop_learning_selected")
    if not item_id:
        await update.message.reply_text("ابتدا دراپ لرنینگ را از فهرست انتخاب کنید.")
        await show_drop_learning_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_DROP_LEARNING_MENU

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "عنوان نمی‌تواند خالی باشد.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_EDIT_TITLE


async def admin_drop_learning_add_content_item(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Add a new content item to existing drop learning."""
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("drop_learning_flow") or {}
    item_id = flow.get("item_id")
    
    if not item_id:
        await update.message.reply_text("خطا در شناسایی دراپ لرنینگ.")
        await show_drop_learning_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_DROP_LEARNING_MENU
    
    file_id = None
    file_type = None
    
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        file_type = "voice"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video_note:
        file_id = update.message.video_note.file_id
        file_type = "video_note"
    
    if file_id and file_type:
        # Get current content count to set order
        content_items = list(database.get_drop_learning_content(item_id))
        order = len(content_items)

        database.add_drop_learning_content(item_id, file_id, file_type, order)
        await update.message.reply_text("محتوا با موفقیت اضافه شد ✅")
        # Return to manage content state - user can add more or go back
        await update.message.reply_text(
            "می‌توانید محتوای دیگری اضافه کنید یا به مدیریت محتوا بازگردید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("بازگشت به مدیریت محتوا", callback_data="drop_learning:manage_content")],
                [InlineKeyboardButton("انصراف 🔙", callback_data="drop_learning:menu")]
            ])
        )
        return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT
    else:
        await update.message.reply_text(
            "لطفاً یک فایل (ویدیو، وویس، فایل و...) ارسال کنید.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT_ITEM


async def admin_drop_learning_edit_content_item(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Edit (replace) an existing content item."""
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("drop_learning_flow") or {}
    content_id = flow.get("content_id")
    item_id = flow.get("item_id")
    
    if not content_id or not item_id:
        await update.message.reply_text("خطا در شناسایی محتوا.")
        await show_drop_learning_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_DROP_LEARNING_MENU
    
    file_id = None
    file_type = None
    
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        file_type = "voice"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video_note:
        file_id = update.message.video_note.file_id
        file_type = "video_note"
    
    if file_id and file_type:
        if database.update_drop_learning_content(content_id, file_id, file_type):
            await update.message.reply_text("محتوا با موفقیت به‌روزرسانی شد ✅")
            context.user_data.pop("drop_learning_flow", None)
            # Return to manage content - user can continue managing or go back
            await update.message.reply_text(
                "برای مشاهده لیست محتواها، دکمه زیر را بزنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("بازگشت به مدیریت محتوا", callback_data="drop_learning:manage_content")],
                    [InlineKeyboardButton("انصراف 🔙", callback_data="drop_learning:menu")]
                ])
            )
            return ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT
        else:
            await update.message.reply_text(
                "خطا در به‌روزرسانی محتوا.",
                reply_markup=DROP_LEARNING_CANCEL_MARKUP,
            )
            return ADMIN_PANEL_DROP_LEARNING_EDIT_CONTENT_ITEM
    else:
        await update.message.reply_text(
            "لطفاً یک فایل (ویدیو، وویس، فایل و...) ارسال کنید.",
            reply_markup=DROP_LEARNING_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_DROP_LEARNING_EDIT_CONTENT_ITEM

    database.update_drop_learning(item_id, title=title)
    context.user_data.pop("drop_learning_flow", None)
    await update.message.reply_text("عنوان دراپ لرنینگ به‌روزرسانی شد ✅")
    await show_drop_learning_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_DROP_LEARNING_MENU


# Case Studies message handlers
async def admin_case_studies_add_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "عنوان کیس استادی نمی‌تواند خالی باشد.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_ADD_TITLE

    flow = context.user_data.get("case_studies_flow") or {}
    flow["title"] = title
    context.user_data["case_studies_flow"] = flow
    await update.message.reply_text(
        "توضیحات کیس استادی را ارسال کنید.",
        reply_markup=CASE_STUDIES_CANCEL_MARKUP,
    )
    return ADMIN_PANEL_CASE_STUDIES_ADD_DESCRIPTION


async def admin_case_studies_add_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("case_studies_flow") or {}
    title = flow.get("title")
    if not title:
        await update.message.reply_text(
            "عنوان کیس استادی مشخص نیست.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_ADD_TITLE

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات کیس استادی نمی‌تواند خالی باشد.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_ADD_DESCRIPTION

    flow["description"] = description
    context.user_data["case_studies_flow"] = flow
    await update.message.reply_text(
        "عکس کاور کیس استادی را ارسال کنید (یا /skip برای رد کردن).",
        reply_markup=CASE_STUDIES_CANCEL_MARKUP,
    )
    return ADMIN_PANEL_CASE_STUDIES_ADD_COVER


async def admin_case_studies_add_cover(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("case_studies_flow") or {}
    
    if update.message.text and update.message.text.strip() == "/skip":
        flow["cover_photo_file_id"] = None
    elif update.message.photo:
        photo = update.message.photo[-1]
        flow["cover_photo_file_id"] = photo.file_id
    else:
        await update.message.reply_text(
            "لطفاً یک عکس ارسال کنید یا /skip را بزنید.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_ADD_COVER

    context.user_data["case_studies_flow"] = flow
    await update.message.reply_text(
        "محتوای کیس استادی را ارسال کنید (ویدیو، وویس، فایل و...).\n"
        "می‌توانید چندین محتوا ارسال کنید.\n"
        "بعد از اتمام، دکمه «پایان ✅» را بزنید.",
        reply_markup=CASE_STUDIES_CONTENT_MARKUP,
    )
    return ADMIN_PANEL_CASE_STUDIES_ADD_CONTENT


async def admin_case_studies_add_content(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    flow = context.user_data.get("case_studies_flow") or {}
    content_items = flow.get("content_items", [])
    
    file_id = None
    file_type = None
    
    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        file_type = "voice"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        file_type = "audio"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video_note:
        file_id = update.message.video_note.file_id
        file_type = "video_note"
    
    if file_id and file_type:
        content_items.append({
            "file_id": file_id,
            "file_type": file_type,
            "order": len(content_items)
        })
        flow["content_items"] = content_items
        context.user_data["case_studies_flow"] = flow
        await update.message.reply_text(
            f"محتوای {len(content_items)} ثبت شد.\n"
            "می‌توانید محتوای دیگری ارسال کنید یا دکمه «پایان ✅» را بزنید.",
            reply_markup=CASE_STUDIES_CONTENT_MARKUP,
        )
    else:
        await update.message.reply_text(
            "لطفاً یک فایل (ویدیو، وویس، فایل و...) ارسال کنید.",
            reply_markup=CASE_STUDIES_CONTENT_MARKUP,
        )
    
    return ADMIN_PANEL_CASE_STUDIES_ADD_CONTENT


async def admin_case_studies_edit_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    item_id = context.user_data.get("case_studies_selected")
    if not item_id:
        await update.message.reply_text("ابتدا کیس استادی را از فهرست انتخاب کنید.")
        await show_case_studies_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_CASE_STUDIES_MENU

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات جدید نمی‌تواند خالی باشد.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_EDIT_DESCRIPTION

    database.update_case_study(item_id, description=description)
    context.user_data.pop("case_studies_flow", None)
    await update.message.reply_text("توضیحات کیس استادی به‌روزرسانی شد ✅")
    await show_case_studies_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_CASE_STUDIES_MENU


async def admin_case_studies_edit_title(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END
    if not await ensure_registered_user(update, context):
        return ConversationHandler.END
    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    item_id = context.user_data.get("case_studies_selected")
    if not item_id:
        await update.message.reply_text("ابتدا کیس استادی را از فهرست انتخاب کنید.")
        await show_case_studies_menu(update.effective_chat.id, context)
        return ADMIN_PANEL_CASE_STUDIES_MENU

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "عنوان نمی‌تواند خالی باشد.",
            reply_markup=CASE_STUDIES_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_CASE_STUDIES_EDIT_TITLE

    database.update_case_study(item_id, title=title)
    context.user_data.pop("case_studies_flow", None)
    await update.message.reply_text("عنوان کیس استادی به‌روزرسانی شد ✅")
    await show_case_studies_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_CASE_STUDIES_MENU


async def show_remove_admin_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="remove:back")])

    await query.edit_message_text(
        "یکی از ادمین‌ها را برای حذف انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def format_admin_list_text() -> str:
    """Format admin list as text."""
    admins = list(database.list_admins())
    # Filter out temp admins from the list
    real_admins = [a for a in admins if a["telegram_id"] not in TEMP_ADMIN_IDS]
    
    if not real_admins:
        return "ادمینی ثبت نشده است."
    
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

    for idx, record in enumerate(real_admins, start=1):
        phone_display = record["phone_number"] or ""
        full_name = " ".join(
            part for part in (record["fname"], record["lname"]) if part
        ).strip() or "بدون نام"
        username = f"@{record['username']}" if record["username"] else ""
        
        admin_info = [number_to_emoji(idx), f"نام: {full_name}"]
        if username:
            admin_info.append(f"یوزرنیم: {username}")
        if phone_display:
            admin_info.append(f"شماره: {phone_display}")
        
        lines.append("\n".join(admin_info))

    return "\n\n".join(lines)


async def reply_with_admin_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    edit_message: bool = False,
) -> None:
    text = format_admin_list_text()

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

    if not update.message:
        return ADMIN_PANEL_ADD_PHONE

    # Accept both text and contact
    phone_input = None
    if update.message.contact:
        phone_input = update.message.contact.phone_number
    elif update.message.text:
        phone_input = update.message.text.strip()
    else:
        await update.message.reply_text(
            "لطفاً شماره موبایل را ارسال کنید (۱۰ رقم پایانی).",
            reply_markup=admin_add_cancel_keyboard(),
        )
        return ADMIN_PANEL_ADD_PHONE

    phone_number = extract_phone_last10(phone_input)
    if not phone_number:
        if update.message:
            await update.message.reply_text(
                "شماره موبایل معتبر نیست. لطفاً دوباره شماره را ارسال کنید (۱۰ رقم پایانی).",
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


async def handle_consultation_approval(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle consultation request approval."""
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.answer("شما به این بخش دسترسی ندارید.", show_alert=True)
        return

    try:
        request_id = int(query.data.split(":")[-1])
    except (ValueError, IndexError):
        await query.answer("درخواست نامعتبر است.", show_alert=True)
        return

    request = database.get_consultation_request(request_id)
    if not request:
        await query.answer("درخواست یافت نشد.", show_alert=True)
        return

    if request["status"] != "pending":
        await query.answer("این درخواست قبلاً پردازش شده است.", show_alert=True)
        return

    # Update status
    database.update_consultation_request_status(request_id, "approved")

    # Send confirmation to user
    try:
        await context.bot.send_message(
            chat_id=request["user_id"],
            text="✅ درخواست مشاوره شما تایید شد.",
        )
    except Exception as e:
        logging.warning(f"Failed to send approval message to user {request['user_id']}: {e}")

    # Request custom message from admin
    context.user_data["consultation_send_message"] = request_id
    context.user_data["consultation_user_id"] = request["user_id"]

    await query.edit_message_caption(
        caption=query.message.caption + "\n\n✅ تایید شد. لطفاً پیام دلخواه خود را برای کاربر ارسال کنید:",
    )


async def handle_consultation_rejection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle consultation request rejection."""
    query = update.callback_query
    await query.answer()

    if not await ensure_private_chat(update, context):
        return

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        await query.answer("شما به این بخش دسترسی ندارید.", show_alert=True)
        return

    try:
        request_id = int(query.data.split(":")[-1])
    except (ValueError, IndexError):
        await query.answer("درخواست نامعتبر است.", show_alert=True)
        return

    request = database.get_consultation_request(request_id)
    if not request:
        await query.answer("درخواست یافت نشد.", show_alert=True)
        return

    if request["status"] != "pending":
        await query.answer("این درخواست قبلاً پردازش شده است.", show_alert=True)
        return

    # Request rejection reason
    context.user_data["consultation_reject"] = request_id
    context.user_data["consultation_user_id"] = request["user_id"]

    await query.edit_message_caption(
        caption=query.message.caption + "\n\n❌ رد شد. لطفاً دلیل رد را بنویسید:",
    )


async def handle_consultation_rejection_reason(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle rejection reason input."""
    if not await ensure_private_chat(update, context):
        return

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        return

    request_id = context.user_data.get("consultation_reject")
    user_id = context.user_data.get("consultation_user_id")

    if not request_id or not user_id:
        return

    if not update.message or not update.message.text:
        await update.message.reply_text("لطفاً یک متن ارسال کنید.")
        return

    rejection_reason = update.message.text.strip()
    if not rejection_reason:
        await update.message.reply_text("دلیل رد نمی‌تواند خالی باشد.")
        return

    # Update status with reason
    database.update_consultation_request_status(request_id, "rejected", rejection_reason)

    # Send rejection message to user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ درخواست مشاوره شما رد شد.\n\nدلیل: {rejection_reason}",
        )
    except Exception as e:
        logging.warning(f"Failed to send rejection message to user {user_id}: {e}")

    context.user_data.pop("consultation_reject", None)
    context.user_data.pop("consultation_user_id", None)

    await update.message.reply_text("پیام رد به کاربر ارسال شد.")


async def handle_consultation_custom_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle custom message for approved consultation."""
    if not await ensure_private_chat(update, context):
        return

    user = update.effective_user
    if not user or not is_admin_user(user.id):
        return

    request_id = context.user_data.get("consultation_send_message")
    user_id = context.user_data.get("consultation_user_id")

    if not request_id or not user_id:
        return

    if not update.message:
        return

    # Forward message to user (supports text, photo, document, etc.)
    try:
        if update.message.text:
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=update.message.photo[-1].file_id,
                caption=update.message.caption,
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=user_id,
                document=update.message.document.file_id,
                caption=update.message.caption,
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=user_id,
                video=update.message.video.file_id,
                caption=update.message.caption,
            )
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=user_id,
                voice=update.message.voice.file_id,
                caption=update.message.caption,
            )
        else:
            await update.message.reply_text("این نوع پیام پشتیبانی نمی‌شود.")
            return

        context.user_data.pop("consultation_send_message", None)
        context.user_data.pop("consultation_user_id", None)
        await update.message.reply_text("پیام به کاربر ارسال شد.")
    except Exception as e:
        logging.warning(f"Failed to send custom message to user {user_id}: {e}")
        await update.message.reply_text("خطا در ارسال پیام.")


async def admin_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data.pop("broadcast_target", None)
    context.user_data.pop("webinar_flow", None)
    context.user_data.pop("webinar_selected", None)
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


# Drop Learning functions (similar to webinar functions)
DROP_LEARNING_CANCEL_MARKUP = InlineKeyboardMarkup(
    [[InlineKeyboardButton("انصراف 🔙", callback_data="drop_learning:menu")]]
)

DROP_LEARNING_CONTENT_MARKUP = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("پایان ✅", callback_data="drop_learning:finish")],
        [InlineKeyboardButton("انصراف 🔙", callback_data="drop_learning:menu")],
    ]
)


def _drop_learning_preview_label(description: str) -> str:
    first_line = (description or "").strip().splitlines()[0] if description else ""
    if not first_line:
        first_line = "دراپ لرنینگ بدون عنوان"
    if len(first_line) > 40:
        return f"{first_line[:37]}..."
    return first_line


async def show_drop_learning_menu(
    target, context: ContextTypes.DEFAULT_TYPE, status: str | None = None
) -> None:
    items = list(database.list_drop_learning())
    keyboard = [
        [InlineKeyboardButton("➕ افزودن دراپ لرنینگ", callback_data="drop_learning:add")]
    ]
    for item in items:
        keyboard.append(
            [
                InlineKeyboardButton(
                    (item["title"] or "").strip()
                    or _drop_learning_preview_label(item["description"]),
                    callback_data=f"drop_learning:select:{item['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="drop_learning:back")])

    text = "مدیریت دراپ لرنینگ:"
    if status:
        text += f"\n\n{status}"
    if not items:
        text += "\n\nدراپ لرنینگی ثبت نشده است."

    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(target, "edit_message_text"):
        try:
            await target.edit_message_text(text, reply_markup=markup)
        except Exception:
            # If edit fails, send new message
            await context.bot.send_message(chat_id=target.message.chat_id, text=text, reply_markup=markup)
    else:
        await context.bot.send_message(chat_id=target, text=text, reply_markup=markup)


async def show_selected_drop_learning(
    query, item: dict[str, str], status: str | None = None
) -> None:
    text_parts = []
    if status:
        text_parts.append(status)
        text_parts.append("")
    text_parts.append("مشخصات دراپ لرنینگ انتخاب‌شده:")
    text_parts.append("")
    text_parts.append(f"عنوان: {item['title'] or 'دراپ لرنینگ بدون عنوان'}")
    text_parts.append("")
    text_parts.append(item["description"])
    text = "\n".join(text_parts)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ویرایش عنوان 🏷️", callback_data="drop_learning:edit_title")],
            [InlineKeyboardButton("ویرایش توضیحات 📝", callback_data="drop_learning:edit_desc")],
            [InlineKeyboardButton("مدیریت محتوا 📎", callback_data="drop_learning:manage_content")],
            [InlineKeyboardButton("حذف دراپ لرنینگ 🗑️", callback_data="drop_learning:delete")],
            [InlineKeyboardButton("بازگشت 🔙", callback_data="drop_learning:menu")],
        ]
    )
    await query.edit_message_text(text, reply_markup=keyboard)


async def show_drop_learning_content_list(
    query, context: ContextTypes.DEFAULT_TYPE, item_id: int, status: str | None = None
) -> None:
    """Show list of content items for a drop learning."""
    item = database.get_drop_learning(item_id)
    if not item:
        await query.answer("این دراپ لرنینگ وجود ندارد.", show_alert=True)
        await show_drop_learning_menu(query, context)
        return

    content_items = list(database.get_drop_learning_content(item_id))
    
    text_parts = []
    if status:
        text_parts.append(status)
        text_parts.append("")
    text_parts.append("مدیریت محتوای دراپ لرنینگ:")
    text_parts.append(f"عنوان: {item['title'] or 'دراپ لرنینگ بدون عنوان'}")
    text_parts.append("")
    
    if content_items:
        text_parts.append(f"تعداد محتوا: {len(content_items)}")
        text_parts.append("")
        for idx, content_item in enumerate(content_items, 1):
            file_type_labels = {
                "video": "ویدیو",
                "voice": "صدا",
                "audio": "آهنگ",
                "document": "فایل",
                "photo": "عکس",
                "video_note": "ویدیو نوت",
            }
            file_type_label = file_type_labels.get(content_item["file_type"], content_item["file_type"])
            text_parts.append(f"{idx}. {file_type_label}")
    else:
        text_parts.append("هیچ محتوایی ثبت نشده است.")
    
    text = "\n".join(text_parts)

    keyboard = []
    keyboard.append([InlineKeyboardButton("➕ افزودن محتوا", callback_data="drop_learning:content:add")])
    
    if content_items:
        for content_item in content_items:
            file_type_labels = {
                "video": "📹",
                "voice": "🎤",
                "audio": "🎵",
                "document": "📄",
                "photo": "🖼️",
                "video_note": "📹",
            }
            icon = file_type_labels.get(content_item["file_type"], "📎")
            keyboard.append([
                InlineKeyboardButton(
                    f"{icon} ویرایش",
                    callback_data=f"drop_learning:content:edit:{content_item['id']}"
                ),
                InlineKeyboardButton(
                    "🗑️ حذف",
                    callback_data=f"drop_learning:content:delete:{content_item['id']}"
                ),
            ])
    
    keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="drop_learning:menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# Case Studies functions (similar to webinar functions)
CASE_STUDIES_CANCEL_MARKUP = InlineKeyboardMarkup(
    [[InlineKeyboardButton("انصراف 🔙", callback_data="case_studies:menu")]]
)

CASE_STUDIES_CONTENT_MARKUP = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("پایان ✅", callback_data="case_studies:finish")],
        [InlineKeyboardButton("انصراف 🔙", callback_data="case_studies:menu")],
    ]
)


def _case_studies_preview_label(description: str) -> str:
    first_line = (description or "").strip().splitlines()[0] if description else ""
    if not first_line:
        first_line = "کیس استادی بدون عنوان"
    if len(first_line) > 40:
        return f"{first_line[:37]}..."
    return first_line


async def show_case_studies_menu(
    target, context: ContextTypes.DEFAULT_TYPE, status: str | None = None
) -> None:
    items = list(database.list_case_studies())
    keyboard = [
        [InlineKeyboardButton("➕ افزودن کیس استادی", callback_data="case_studies:add")]
    ]
    for item in items:
        keyboard.append(
            [
                InlineKeyboardButton(
                    (item["title"] or "").strip()
                    or _case_studies_preview_label(item["description"]),
                    callback_data=f"case_studies:select:{item['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("بازگشت 🔙", callback_data="case_studies:back")])

    text = "مدیریت کیس استادی:"
    if status:
        text += f"\n\n{status}"
    if not items:
        text += "\n\nکیس استادی ثبت نشده است."

    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(target, "edit_message_text"):
        try:
            await target.edit_message_text(text, reply_markup=markup)
        except Exception:
            # If edit fails, send new message
            await context.bot.send_message(chat_id=target.message.chat_id, text=text, reply_markup=markup)
    else:
        await context.bot.send_message(chat_id=target, text=text, reply_markup=markup)


async def show_selected_case_study(
    query, item: dict[str, str], status: str | None = None
) -> None:
    text_parts = []
    if status:
        text_parts.append(status)
        text_parts.append("")
    text_parts.append("مشخصات کیس استادی انتخاب‌شده:")
    text_parts.append("")
    text_parts.append(f"عنوان: {item['title'] or 'کیس استادی بدون عنوان'}")
    text_parts.append("")
    text_parts.append(item["description"])
    text = "\n".join(text_parts)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ویرایش عنوان 🏷️", callback_data="case_studies:edit_title")],
            [InlineKeyboardButton("ویرایش توضیحات 📝", callback_data="case_studies:edit_desc")],
            [InlineKeyboardButton("حذف کیس استادی 🗑️", callback_data="case_studies:delete")],
            [InlineKeyboardButton("بازگشت 🔙", callback_data="case_studies:menu")],
        ]
    )
    await query.edit_message_text(text, reply_markup=keyboard)


def create_admin_conversation() -> ConversationHandler:
    private_text = filters.ChatType.PRIVATE & filters.TEXT

    return ConversationHandler(
        entry_points=[
            CommandHandler("panel", admin_panel_entry, filters=filters.ChatType.PRIVATE),
            MessageHandler(
                private_text & filters.Regex("^🛠️ پنل ادمین$"), admin_panel_entry
            ),
        ],
        states={
            ADMIN_PANEL_MAIN: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_panel_main_message
                ),
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
                MessageHandler(
                    filters.ChatType.PRIVATE & (filters.TEXT | filters.CONTACT) & ~filters.COMMAND,
                    admin_add_phone
                ),
                CallbackQueryHandler(admin_add_cancel_callback, pattern="^add:cancel$"),
            ],
            ADMIN_PANEL_REMOVE_PHONE: [
                CallbackQueryHandler(handle_remove_admin_selection, pattern="^remove:"),
            ],
            ADMIN_PANEL_WEBINAR_MENU: [
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_ADD_TITLE: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_add_title
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_add_description
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_ADD_COVER: [
                MessageHandler(
                    filters.PHOTO | (filters.TEXT & filters.Regex("^/skip$")),
                    admin_webinar_add_cover
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_ADD_CONTENT: [
                MessageHandler(
                    filters.VIDEO | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO_NOTE,
                    admin_webinar_add_content
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_edit_description
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_EDIT_TITLE: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_edit_title
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_MENU: [
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_ADD_TITLE: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_drop_learning_add_title
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_ADD_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_drop_learning_add_description
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_ADD_COVER: [
                MessageHandler(
                    filters.PHOTO | (filters.TEXT & filters.Regex("^/skip$")),
                    admin_drop_learning_add_cover
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT: [
                MessageHandler(
                    filters.VIDEO | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO_NOTE,
                    admin_drop_learning_add_content
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_EDIT_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_drop_learning_edit_description
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_MANAGE_CONTENT: [
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT_ITEM: [
                MessageHandler(
                    filters.VIDEO | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO_NOTE,
                    admin_drop_learning_add_content_item
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_EDIT_CONTENT_ITEM: [
                MessageHandler(
                    filters.VIDEO | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO_NOTE,
                    admin_drop_learning_edit_content_item
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_DROP_LEARNING_EDIT_TITLE: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_drop_learning_edit_title
                ),
                CallbackQueryHandler(admin_panel_drop_learning_callback, pattern="^drop_learning:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_MENU: [
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_ADD_TITLE: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_case_studies_add_title
                ),
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_ADD_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_case_studies_add_description
                ),
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_ADD_COVER: [
                MessageHandler(
                    filters.PHOTO | (filters.TEXT & filters.Regex("^/skip$")),
                    admin_case_studies_add_cover
                ),
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_ADD_CONTENT: [
                MessageHandler(
                    filters.VIDEO | filters.VOICE | filters.AUDIO | filters.Document.ALL | filters.PHOTO | filters.VIDEO_NOTE,
                    admin_case_studies_add_content
                ),
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_EDIT_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_case_studies_edit_description
                ),
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
            ADMIN_PANEL_CASE_STUDIES_EDIT_TITLE: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_case_studies_edit_title
                ),
                CallbackQueryHandler(admin_panel_case_studies_callback, pattern="^case_studies:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_cancel)],
        allow_reentry=True,
    )


__all__ = [
    "admin_broadcast_message",
    "admin_cancel",
    "admin_panel_entry",
    "create_admin_conversation",
    "handle_consultation_approval",
    "handle_consultation_custom_message",
    "handle_consultation_rejection",
    "handle_consultation_rejection_reason",
    "handle_remove_admin_selection",
    "reply_with_admin_list",
    "show_remove_admin_menu",
]