"""Shared constants used across bot modules."""

from typing import Dict, Optional

TEMP_ADMIN_IDS = {234368567}

(
    ADMIN_PANEL_MAIN,
    ADMIN_PANEL_SETTINGS,
    ADMIN_PANEL_MANAGE,
    ADMIN_PANEL_ADD_PHONE,
    ADMIN_PANEL_REMOVE_PHONE,
    ADMIN_PANEL_BROADCAST_MENU,
    ADMIN_PANEL_BROADCAST_MESSAGE,
    ADMIN_PANEL_WEBINAR_MENU,
    ADMIN_PANEL_WEBINAR_ADD_TITLE,
    ADMIN_PANEL_WEBINAR_ADD_DESCRIPTION,
    ADMIN_PANEL_WEBINAR_ADD_COVER,
    ADMIN_PANEL_WEBINAR_ADD_CONTENT,
    ADMIN_PANEL_WEBINAR_EDIT_TITLE,
    ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION,
    # Drop Learning states
    ADMIN_PANEL_DROP_LEARNING_MENU,
    ADMIN_PANEL_DROP_LEARNING_ADD_TITLE,
    ADMIN_PANEL_DROP_LEARNING_ADD_DESCRIPTION,
    ADMIN_PANEL_DROP_LEARNING_ADD_COVER,
    ADMIN_PANEL_DROP_LEARNING_ADD_CONTENT,
    ADMIN_PANEL_DROP_LEARNING_EDIT_TITLE,
    ADMIN_PANEL_DROP_LEARNING_EDIT_DESCRIPTION,
    # Case Studies states
    ADMIN_PANEL_CASE_STUDIES_MENU,
    ADMIN_PANEL_CASE_STUDIES_ADD_TITLE,
    ADMIN_PANEL_CASE_STUDIES_ADD_DESCRIPTION,
    ADMIN_PANEL_CASE_STUDIES_ADD_COVER,
    ADMIN_PANEL_CASE_STUDIES_ADD_CONTENT,
    ADMIN_PANEL_CASE_STUDIES_EDIT_TITLE,
    ADMIN_PANEL_CASE_STUDIES_EDIT_DESCRIPTION,
) = range(28)

MEMBERSHIP_VERIFY_CALLBACK = "verify_membership"

BROADCAST_OPTIONS: Dict[str, Dict[str, Optional[bool]]] = {
    "broadcast:all": {"label": "همه کاربران", "filter": None},
    "broadcast:with_phone": {"label": "کاربران دارای شماره", "filter": True},
    "broadcast:without_phone": {"label": "کاربران بدون شماره", "filter": False},
}

CORE_MENU_BUTTONS = [
    "Case Studies",
    "وبینار ها",
    "دراپ لرنینگ",
    "رزرو مشاوره",
    "خدمات",
]

SERVICE_BUTTONS = [
    "طراحی سایت",
    "تولید محتوا",
    "مشاوره فروش و بازاریابی",
    "کمپین فروش",
    "تیم سازی و منابع انسانی",
    "برندینگ",
]

# Payment information - can be configured via environment variables
PAYMENT_AMOUNT = "500000"  # تومان
PAYMENT_CARD_NUMBER = "6037-1234-5678-9012"  # شماره کارت

CONSULTATION_MESSAGE = """قرار نیست حرفای تئوری بشنوی.

مسئله‌ت رو بیار،

من ریشه‌ش رو پیدا می‌کنم،

و راه‌حل عملی و قابل اجرا بهت می‌دم.

🔸 رشد فروش

🔸 بازاریابی

🔸 برند

🔸 منابع انسانی و فرهنگ سازمانی

🔸 سیستم‌سازی و نظم‌دهی به کسب‌وکار

اگه نمی‌خوای وقت و پول بیشتری پای آزمون‌وخطا بریزه،

مشاوره‌ت رو رزرو کن تا مسیر درست رو سریع‌تر پیدا کنیم."""

CORE_MENU_RESPONSES = {}

SERVICE_RESPONSES = {
    "طراحی سایت": "خدمت طراحی سایت به زودی در دسترس قرار می‌گیرد.",
    "تولید محتوا": "خدمت تولید محتوا به زودی در دسترس قرار می‌گیرد.",
    "مشاوره فروش و بازاریابی": "خدمت مشاوره فروش و بازاریابی به زودی در دسترس قرار می‌گیرد.",
    "کمپین فروش": "خدمت کمپین فروش به زودی در دسترس قرار می‌گیرد.",
    "تیم سازی و منابع انسانی": "خدمت تیم سازی و منابع انسانی به زودی در دسترس قرار می‌گیرد.",
    "برندینگ": "خدمت برندینگ به زودی در دسترس قرار می‌گیرد.",
}


