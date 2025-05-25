from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from app.config import WEBAPP_URL, RESORT_PHONE, RESORT_ADMIN_USERNAME


# Главная клавиатура с новыми функциями
def main_keyboard():
    kb = [
        [KeyboardButton(text="🏨 О курорте"), KeyboardButton(text="🛏️ Номера")],
        [KeyboardButton(text="📝 Бронирование", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="🎥 Виртуальные туры")],  # НОВАЯ КНОПКА
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


# Клавиатура для детального просмотра номера с видео
def room_detail_keyboard(room_id, has_video=False):
    kb = [
        [
            InlineKeyboardButton(text="📝 Забронировать", web_app=WebAppInfo(url=f"{WEBAPP_URL}?room_id={room_id}")),
            InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"reviews_{room_id}")
        ]
    ]

    # Добавляем кнопки для медиа если есть
    if has_video:
        kb.append([
            InlineKeyboardButton(text="🎥 Видео-тур", callback_data=f"video_tour_{room_id}"),
            InlineKeyboardButton(text="📸 Все фото", callback_data=f"all_photos_{room_id}")
        ])

    kb.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_rooms")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Клавиатура умного помощника
def assistant_keyboard():
    kb = [
        [
            InlineKeyboardButton(text="🏠 Подобрать номер", callback_data="assist_room_selection"),
            InlineKeyboardButton(text="📅 Проверить даты", callback_data="assist_check_dates")
        ],
        [
            InlineKeyboardButton(text="💰 Узнать цены", callback_data="assist_pricing"),
            InlineKeyboardButton(text="🚗 Как добраться", callback_data="assist_location")
        ],
        [
            InlineKeyboardButton(text="👨‍👩‍👧‍👦 Отдых с детьми", callback_data="assist_family"),
            InlineKeyboardButton(text="🎉 Корпоративы", callback_data="assist_corporate")
        ],
        [
            InlineKeyboardButton(text="❓ Частые вопросы", callback_data="assist_faq"),
            InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{RESORT_ADMIN_USERNAME}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# Клавиатура для моих бронирований
def my_bookings_keyboard(bookings):
    kb = []

    for booking in bookings[:5]:  # Показываем последние 5
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "cancelled": "❌"
        }.get(booking.status, "📋")

        kb.append([InlineKeyboardButton(
            text=f"{status_emoji} #{booking.id} | {booking.check_in.strftime('%d.%m')} | {booking.room.name[:20]}",
            callback_data=f"booking_detail_{booking.id}"
        )])

    if len(bookings) > 5:
        kb.append([InlineKeyboardButton(
            text="📋 Показать все бронирования",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/my-bookings")
        )])

    kb.append([InlineKeyboardButton(
        text="📝 Новое бронирование",
        callback_data="new_booking"
    )])

    return InlineKeyboardMarkup(inline_keyboard=kb)
# Клавиатура для акций и спецпредложений
def promotions_keyboard():
    kb = [
        [InlineKeyboardButton(text="🎁 Скидка выходного дня", callback_data="promo_weekend")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Семейный пакет", callback_data="promo_family")],
        [InlineKeyboardButton(text="🎂 День рождения в подарок", callback_data="promo_birthday")],
        [InlineKeyboardButton(text="⭐ Программа лояльности", callback_data="loyalty_program")],
        [InlineKeyboardButton(text="📢 Подписаться на акции", callback_data="subscribe_promos")]
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