"""Handler registration for the Telegram bot."""

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .admin.conversation import create_admin_conversation
from .constants import MEMBERSHIP_VERIFY_CALLBACK
from .menu import (
    handle_contact,
    handle_membership_verification,
    handle_menu_selection,
    handle_register_phone_callback,
    handle_sendphone_command,
    start,
)


def register_handlers(application: Application) -> None:
    admin_panel_handler = create_admin_conversation()
    private_text = filters.ChatType.PRIVATE & filters.TEXT

    application.add_handler(
        CallbackQueryHandler(
            handle_membership_verification,
            pattern=f"^{MEMBERSHIP_VERIFY_CALLBACK}$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            handle_register_phone_callback,
            pattern="^register_phone$",
        )
    )
    application.add_handler(
        CommandHandler("start", start, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(
        CommandHandler("sendphone", handle_sendphone_command, filters=filters.ChatType.PRIVATE)
    )
    application.add_handler(admin_panel_handler)
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.CONTACT, handle_contact)
    )
    application.add_handler(
        MessageHandler(private_text & ~filters.COMMAND, handle_menu_selection)
    )


__all__ = ["register_handlers"]


