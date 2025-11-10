import logging

import database
from bot import configure_channel, create_application, get_bot_token, load_env


def main() -> None:
    load_env()
    database.init_db()
    token = get_bot_token()
    configure_channel()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    application = create_application(token)
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()

