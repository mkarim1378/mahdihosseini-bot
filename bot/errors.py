"""Error handling utilities."""

import logging

from telegram import Update
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import ContextTypes


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


__all__ = ["handle_error"]


