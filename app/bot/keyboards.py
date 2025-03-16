from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import WEBAPP_URL

# Main keyboard
def main_keyboard():
    kb = [
        [KeyboardButton(text="🏨 О курорте"), KeyboardButton(text="🛏️ Номера")],
        [KeyboardButton(text="📝 Бронирование", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="📞 Связь с поддержкой"), KeyboardButton(text="⭐ Отзывы")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Rooms keyboard
def rooms_keyboard(rooms):
    kb = []
    for room in rooms:
        kb.append([
            InlineKeyboardButton(
                text=f"{room.name} - {room.price_per_night}₽/ночь",
                callback_data=f"room_{room.id}"
            )
        ])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Room detail keyboard
def room_detail_keyboard(room_id):
    kb = [
        [
            InlineKeyboardButton(text="📝 Забронировать", web_app=WebAppInfo(url=f"{WEBAPP_URL}?room_id={room_id}")),
            InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"reviews_{room_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_rooms")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Support keyboard
def support_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="📱 Позвонить", callback_data="call_support"),
            InlineKeyboardButton(text="✉️ Написать администратору", url="https://t.me/admin_username")
        ],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)