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
    ADMIN_PANEL_WEBINAR_ADD_LINK,
    ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION,
    ADMIN_PANEL_WEBINAR_EDIT_LINK,
    ADMIN_PANEL_WEBINAR_MENU,
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

    if data == "settings:webinars":
        await show_webinar_menu(query, context)
        return ADMIN_PANEL_WEBINAR_MENU

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


WEBINAR_CANCEL_MARKUP = InlineKeyboardMarkup(
    [[InlineKeyboardButton("انصراف 🔙", callback_data="webinar:menu")]]
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
                    _webinar_preview_label(webinar["description"]),
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
        await target.edit_message_text(text, reply_markup=markup)
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
    text_parts.append(webinar["description"])
    text_parts.append("")
    text_parts.append("لینک ثبت‌نام:")
    text_parts.append(webinar["registration_link"])
    text = "\n".join(text_parts)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("ویرایش توضیحات 📝", callback_data="webinar:edit_desc")],
            [InlineKeyboardButton("ویرایش لینک 🔗", callback_data="webinar:edit_link")],
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
        await query.edit_message_text(
            "بخش تنظیمات ربات:",
            reply_markup=admin_settings_keyboard(phone_requirement_enabled(context)),
        )
        return ADMIN_PANEL_SETTINGS

    if data == "webinar:menu":
        context.user_data.pop("webinar_flow", None)
        await show_webinar_menu(query, context)
        return ADMIN_PANEL_WEBINAR_MENU

    if data == "webinar:add":
        context.user_data["webinar_flow"] = {}
        await query.edit_message_text(
            "توضیحات وبینار را ارسال کنید.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION

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

    if data == "webinar:edit_link":
        webinar_id = context.user_data.get("webinar_selected")
        if not webinar_id:
            await query.answer("ابتدا وبینار را انتخاب کنید.", show_alert=True)
            await show_webinar_menu(query, context)
            return ADMIN_PANEL_WEBINAR_MENU
        context.user_data["webinar_flow"] = {"webinar_id": webinar_id}
        await query.edit_message_text(
            "لینک جدید ثبت‌نام را ارسال کنید.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_EDIT_LINK

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

    await query.answer("گزینه نامعتبر است.", show_alert=True)
    await show_webinar_menu(query, context)
    return ADMIN_PANEL_WEBINAR_MENU


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

    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text(
            "توضیحات وبینار نمی‌تواند خالی باشد. لطفاً دوباره ارسال کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION

    context.user_data["webinar_flow"] = {"description": description}
    await update.message.reply_text(
        "لینک ثبت‌نام وبینار را ارسال کن (با http:// یا https://).",
        reply_markup=WEBINAR_CANCEL_MARKUP,
    )
    return ADMIN_PANEL_WEBINAR_ADD_LINK


async def admin_webinar_add_link(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if not await ensure_channel_membership(update, context):
        return ConversationHandler.END

    if not await ensure_registered_user(update, context):
        return ConversationHandler.END

    if not is_admin_user(update.effective_user.id):
        await update.message.reply_text("دسترسی شما قطع شده است.")
        return ConversationHandler.END

    link = (update.message.text or "").strip()
    if not _looks_like_url(link):
        await update.message.reply_text(
            "لینک باید با http:// یا https:// شروع شود. لطفاً دوباره ارسال کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_LINK

    flow = context.user_data.get("webinar_flow") or {}
    description = flow.get("description")
    if not description:
        await update.message.reply_text(
            "اطلاعات وبینار ناقص است. لطفاً دوباره تلاش کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_ADD_LINK

    database.create_webinar(description, link)
    context.user_data.pop("webinar_flow", None)
    await update.message.reply_text("وبینار جدید ثبت شد ✅")
    await show_webinar_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_WEBINAR_MENU


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


async def admin_webinar_edit_link(
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

    link = (update.message.text or "").strip()
    if not _looks_like_url(link):
        await update.message.reply_text(
            "لینک باید با http:// یا https:// شروع شود. دوباره تلاش کن.",
            reply_markup=WEBINAR_CANCEL_MARKUP,
        )
        return ADMIN_PANEL_WEBINAR_EDIT_LINK

    database.update_webinar(webinar_id, registration_link=link)
    context.user_data.pop("webinar_flow", None)
    await update.message.reply_text("لینک ثبت‌نام به‌روزرسانی شد ✅")
    await show_webinar_menu(update.effective_chat.id, context)
    return ADMIN_PANEL_WEBINAR_MENU


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
                    "شماره: نامشخص",
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
            ADMIN_PANEL_WEBINAR_MENU: [
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_add_description
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_ADD_LINK: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_add_link
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_edit_description
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
            ],
            ADMIN_PANEL_WEBINAR_EDIT_LINK: [
                MessageHandler(
                    private_text & ~filters.COMMAND, admin_webinar_edit_link
                ),
                CallbackQueryHandler(admin_panel_webinar_callback, pattern="^webinar:"),
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
    "handle_remove_admin_selection",
    "reply_with_admin_list",
    "show_remove_admin_menu",
]