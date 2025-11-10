"""Application factory for the Telegram bot."""

import os

from telegram.ext import Application

from .errors import handle_error
from .handlers import register_handlers


def create_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    require_phone_env = os.getenv("REQUIRE_PHONE_DEFAULT", "").strip().lower()
    phone_required = require_phone_env in {"1", "true", "yes", "on"}
    application.bot_data.setdefault("require_phone", phone_required)

    register_handlers(application)
    application.add_error_handler(handle_error)
    return application


__all__ = ["create_application"]


