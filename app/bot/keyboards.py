from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import WEBAPP_URL, RESORT_PHONE, RESORT_ADMIN_USERNAME


# Main keyboard
def main_keyboard():
    kb = [
        [KeyboardButton(text="🏨 О курорте"), KeyboardButton(text="🛏️ Номера")],
        [KeyboardButton(text="📝 Бронирование", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="📞 Связь с поддержкой"), KeyboardButton(text="⭐ Отзывы")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# Rooms keyboard с группировкой по типам
def rooms_keyboard(rooms):
    kb = []

    # Группируем номера по типам
    room_types = {
        "standard": "Стандартные номера",
        "luxury": "Люкс номера",
        "vip": "VIP номера",
        "apartment": "Апартаменты",
        "cottage": "Коттеджи",
        "president": "Президентские апартаменты",
        "tapchan": "Тапчаны"
    }

    # Добавляем заголовки для каждого типа
    for room_type, type_name in room_types.items():
        # Фильтруем комнаты по типу
        type_rooms = [r for r in rooms if r.room_type == room_type]

        if type_rooms:
            # Добавляем заголовок типа
            kb.append([InlineKeyboardButton(text=f"🏠 {type_name}", callback_data=f"room_type_{room_type}")])

            # Добавляем кнопки для каждого номера этого типа
            for room in type_rooms:
                # Форматируем цену: ПН-ЧТ / ПТ-ВС если есть weekend_price
                price_text = f"{room.price_per_night}сум"
                if hasattr(room, "weekend_price") and room.weekend_price:
                    price_text = f"{room.price_per_night}сум / {room.weekend_price}сум"

                kb.append([
                    InlineKeyboardButton(
                        text=f"{room.name} - {price_text}",
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


# Support keyboard с обновленной контактной информацией
def support_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="📱 Позвонить", callback_data="call_support"),
            InlineKeyboardButton(text="✉️ Написать администратору", url=f"https://t.me/{RESORT_ADMIN_USERNAME}")
        ],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)