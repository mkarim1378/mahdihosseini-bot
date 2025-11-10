"""Guard helpers that validate chat context and membership requirements."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatMemberStatus, ChatType
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from . import config
from .keyboards import membership_keyboard
from .utils import ensure_user_record, phone_requirement_enabled, prompt_for_contact
import database


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


async def is_user_in_channel(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    channel_identifier = config.CHANNEL_CHAT_IDENTIFIER
    if channel_identifier is None:
        raise RuntimeError(
            "Channel chat identifier is not configured. Ensure CHANNEL_ID (or CHANNEL_CHAT_ID) is set correctly."
        )
    try:
        member = await context.bot.get_chat_member(channel_identifier, user_id)
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


__all__ = [
    "ensure_channel_membership",
    "ensure_private_chat",
    "ensure_registered_user",
    "is_user_in_channel",
    "prompt_for_channel_membership",
]


