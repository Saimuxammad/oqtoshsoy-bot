from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from datetime import datetime, timedelta
import calendar
from typing import List, Tuple, Optional, Dict

from app.config import WEBAPP_URL


# ==================== Клавиатуры для работы с дополнительными услугами ====================

def services_keyboard(services, is_admin=False):
    """Клавиатура для выбора дополнительной услуги"""
    kb = []
    for service in services:
        kb.append([
            InlineKeyboardButton(
                text=f"{service.name} - {service.price:,.0f} сум" + ("/час" if service.is_hourly else ""),
                callback_data=f"service_{service.id}"
            )
        ])

    # Для администратора добавляем кнопки управления
    if is_admin:
        kb.append([InlineKeyboardButton(text="➕ Добавить новую услугу", callback_data="add_service")])

    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def service_detail_keyboard(service_id):
    """Клавиатура для деталей дополнительной услуги"""
    kb = [
        [
            InlineKeyboardButton(text="📝 Забронировать", callback_data=f"book_service_{service_id}")
        ],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_services")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def calendar_keyboard(date):
    """Клавиатура для выбора даты в виде календаря"""
    kb = []

    # Заголовок календаря с текущим месяцем и годом
    year = date.year
    month = date.month
    month_name = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }

    kb.append([
        InlineKeyboardButton(text=f"{month_name[month]} {year}", callback_data="ignore")
    ])

    # Дни недели
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    days_row = []
    for day in days_of_week:
        days_row.append(InlineKeyboardButton(text=day, callback_data="ignore"))
    kb.append(days_row)

    # Определяем первый день месяца и количество дней
    first_day = datetime(year, month, 1)
    num_days = calendar.monthrange(year, month)[1]

    # Создаем пустые ячейки до первого дня месяца
    # В Python понедельник - 0, воскресенье - 6
    first_weekday = first_day.weekday()  # 0 - понедельник, 6 - воскресенье

    # Заполняем календарь днями
    current_row = []
    # Добавляем пустые ячейки до первого дня месяца
    for _ in range(first_weekday):
        current_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    # Сегодняшний день для выделения
    today = datetime.now().date()

    # Минимальная дата для выбора (сегодня)
    min_date = today
    # Максимальная дата для выбора (сегодня + 90 дней)
    max_date = today + timedelta(days=90)

    # Добавляем дни месяца
    for day in range(1, num_days + 1):
        current_date = datetime(year, month, day).date()

        # Проверяем, находится ли дата в допустимом диапазоне
        is_selectable = min_date <= current_date <= max_date

        # Форматируем текст для кнопки
        if current_date == today:
            # Сегодняшний день
            btn_text = f"[{day}]"
        else:
            btn_text = str(day)

        if is_selectable:
            # Кнопка с датой, которую можно выбрать
            btn_data = f"calendar_day_{current_date.strftime('%Y-%m-%d')}"
        else:
            # Неактивная кнопка
            btn_data = "ignore"

        current_row.append(InlineKeyboardButton(text=btn_text, callback_data=btn_data))

        # Если достигли конца недели или конца месяца, добавляем строку в клавиатуру
        if len(current_row) == 7 or day == num_days:
            kb.append(current_row)
            current_row = []

    # Добавляем кнопки навигации
    kb.append([
        InlineKeyboardButton(
            text="« Предыдущий",
            callback_data=f"calendar_prev_{date.strftime('%Y-%m')}"
        ),
        InlineKeyboardButton(
            text="Следующий »",
            callback_data=f"calendar_next_{date.strftime('%Y-%m')}"
        )
    ])

    # Кнопка отмены
    kb.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_booking")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def service_booking_keyboard(available_slots):
    """Клавиатура для выбора времени бронирования услуги"""
    kb = []

    # Группируем по 2 слота в строке
    row = []
    for start_time, end_time in available_slots:
        btn_text = f"{start_time} - {end_time}"
        btn_data = f"time_{start_time}_{end_time}"

        row.append(InlineKeyboardButton(text=btn_text, callback_data=btn_data))

        if len(row) == 2:
            kb.append(row)
            row = []

    # Добавляем оставшиеся слоты
    if row:
        kb.append(row)

    # Кнопка отмены
    kb.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_booking")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def confirm_cancel_keyboard():
    """Клавиатура для подтверждения или отмены действия"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ==================== Клавиатуры для административной панели ====================

def admin_keyboard(admin):
    """Клавиатура для административной панели"""
    kb = []

    # Добавляем кнопки в зависимости от прав доступа
    if admin.can_manage_rooms:
        kb.append([InlineKeyboardButton(text="🛏️ Управление номерами", callback_data="admin_rooms")])

    if admin.can_manage_bookings:
        kb.append([InlineKeyboardButton(text="📝 Управление бронированиями", callback_data="admin_bookings")])

    if admin.can_manage_services:
        kb.append([InlineKeyboardButton(text="🏊‍♂️ Управление доп. услугами", callback_data="admin_services")])

    if admin.is_superadmin:
        kb.append([InlineKeyboardButton(text="👥 Управление администраторами", callback_data="admin_users")])

    kb.append([InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")])
    kb.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=kb)


def room_availability_keyboard():
    """Клавиатура для управления доступностью номеров"""
    kb = [
        [InlineKeyboardButton(text="📅 Календарь занятости", callback_data="room_calendar")],
        [InlineKeyboardButton(text="➕ Добавить номер", callback_data="add_room")],
        [InlineKeyboardButton(text="✏️ Редактировать цены", callback_data="edit_prices")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ==================== Клавиатуры для платежей ====================

def payment_methods_keyboard(booking_id, booking_type="booking"):
    """Клавиатура для выбора способа оплаты"""
    kb = [
        [InlineKeyboardButton(text="💳 PayMe", callback_data=f"pay_{booking_type}_{booking_id}_payme")],
        [InlineKeyboardButton(text="💳 Click", callback_data=f"pay_{booking_type}_{booking_id}_click")],
        [InlineKeyboardButton(text="💵 Оплата при заселении", callback_data=f"pay_{booking_type}_{booking_id}_cash")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ==================== Обновление основной клавиатуры ====================

def updated_main_keyboard():
    """Обновленная основная клавиатура с дополнительными функциями"""
    kb = [
        [KeyboardButton(text="🏨 О курорте"), KeyboardButton(text="🛏️ Номера")],
        [KeyboardButton(text="📝 Бронирование", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="🏊‍♂️ Дополнительные услуги"), KeyboardButton(text="📅 Мои бронирования")],
        [KeyboardButton(text="📞 Связь с поддержкой"), KeyboardButton(text="⭐ Отзывы")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)