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
    ADMIN_PANEL_WEBINAR_ADD_LINK,
    ADMIN_PANEL_WEBINAR_ADD_COVER,
    ADMIN_PANEL_WEBINAR_ADD_CONTENT,
    ADMIN_PANEL_WEBINAR_EDIT_TITLE,
    ADMIN_PANEL_WEBINAR_EDIT_DESCRIPTION,
    ADMIN_PANEL_WEBINAR_EDIT_LINK,
) = range(16)

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
    "مشاوره رایگان",
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

CORE_MENU_RESPONSES = {
    "Case Studies": "بخش Case Studies به زودی در دسترس قرار می‌گیرد.",
    "دراپ لرنینگ": "دراپ لرنینگ به زودی فعال می‌شود.",
    "مشاوره رایگان": "مشاوران ما به زودی پاسخگوی شما خواهند بود.",
}

SERVICE_RESPONSES = {
    "طراحی سایت": "خدمت طراحی سایت به زودی در دسترس قرار می‌گیرد.",
    "تولید محتوا": "خدمت تولید محتوا به زودی در دسترس قرار می‌گیرد.",
    "مشاوره فروش و بازاریابی": "خدمت مشاوره فروش و بازاریابی به زودی در دسترس قرار می‌گیرد.",
    "کمپین فروش": "خدمت کمپین فروش به زودی در دسترس قرار می‌گیرد.",
    "تیم سازی و منابع انسانی": "خدمت تیم سازی و منابع انسانی به زودی در دسترس قرار می‌گیرد.",
    "برندینگ": "خدمت برندینگ به زودی در دسترس قرار می‌گیرد.",
}


