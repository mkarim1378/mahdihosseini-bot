"""Runtime configuration helpers for the Telegram bot."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple, Union

CHANNEL_INVITE_LINK: str = ""
CHANNEL_CHAT_IDENTIFIER: Optional[Union[int, str]] = None


def load_env() -> None:
    """Load key/value pairs from the project .env file into os.environ."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "BOT_TOKEN is missing. Set it in the environment or in the .env file."
        )
    return token


def configure_channel() -> Tuple[str, Union[int, str]]:
    """Populate global channel configuration from environment variables."""
    invite_link, chat_identifier = load_channel_configuration()
    set_channel_configuration(invite_link, chat_identifier)
    return invite_link, chat_identifier


def set_channel_configuration(
    invite_link: str, chat_identifier: Union[int, str]
) -> None:
    global CHANNEL_INVITE_LINK, CHANNEL_CHAT_IDENTIFIER
    CHANNEL_INVITE_LINK = invite_link
    CHANNEL_CHAT_IDENTIFIER = chat_identifier


def load_channel_configuration() -> Tuple[str, Union[int, str]]:
    raw = os.getenv("CHANNEL_ID")
    if not raw:
        raise RuntimeError(
            "CHANNEL_ID is missing. Provide the invite link, @username, or numeric chat ID in the .env file."
        )

    raw_value = raw.strip()
    invite_link = os.getenv("CHANNEL_INVITE_LINK", "").strip()
    chat_identifier_raw: Optional[str] = None

    if raw_value.startswith("http://") or raw_value.startswith("https://"):
        invite_link = raw_value
        chat_identifier_raw = os.getenv("CHANNEL_CHAT_ID")
    else:
        chat_identifier_raw = raw_value
        if not invite_link:
            if raw_value.startswith("@"):
                invite_link = f"https://t.me/{raw_value.lstrip('@')}"
            else:
                if raw_value.startswith("https://t.me/") or raw_value.startswith(
                    "http://t.me/"
                ):
                    invite_link = raw_value
                elif raw_value.startswith("t.me/"):
                    invite_link = f"https://{raw_value}"
                else:
                    raise RuntimeError(
                        "CHANNEL_INVITE_LINK is missing. Provide the channel invite link via CHANNEL_INVITE_LINK when CHANNEL_ID is a numeric ID."
                    )

    if not invite_link:
        raise RuntimeError(
            "CHANNEL_INVITE_LINK is missing. Provide the channel invite link via CHANNEL_ID or CHANNEL_INVITE_LINK."
        )

    chat_identifier = _parse_chat_identifier(chat_identifier_raw)
    return invite_link, chat_identifier


def _parse_chat_identifier(raw: Optional[str]) -> Union[int, str]:
    if raw is None:
        raise RuntimeError(
            "CHANNEL_CHAT_ID is required when CHANNEL_ID is an invite link or does not start with @."
        )

    value = raw.strip()
    if not value:
        raise RuntimeError("CHANNEL_CHAT_ID cannot be empty.")

    if value.startswith("@"):
        return value

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            "CHANNEL_CHAT_ID must be a numeric chat ID or start with @ for public channels."
        ) from exc


