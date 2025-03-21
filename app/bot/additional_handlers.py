from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import calendar
import logging
import re

from app.bot.additional_keyboards import (
    services_keyboard, service_detail_keyboard, calendar_keyboard,
    service_booking_keyboard, confirm_cancel_keyboard, admin_keyboard,
    room_availability_keyboard, payment_methods_keyboard, updated_main_keyboard
)
from app.database.crud import (
    get_user_by_telegram_id, get_or_create_user
)
from app.database.additional_models import AdditionalService, ServiceBooking, BotAdmin, Payment
from app.database.additional_crud import (
    get_all_services, get_available_services, get_service, create_service_booking,
    check_service_availability, get_user_service_bookings, get_service_booking,
    cancel_service_booking, get_bot_admin, check_admin_permissions,
    get_room_occupancy, get_all_rooms_occupancy, create_payment,
    update_payment_status, calculate_booking_price_enhanced
)

# Создаем роутеры для новых обработчиков
services_router = Router()
admin_router = Router()
calendar_router = Router()
payment_router = Router()

# Логгер
logger = logging.getLogger(__name__)


# ============= Состояния FSM для работы с бронированием услуг =============

class ServiceBookingStates(StatesGroup):
    selecting_service = State()
    selecting_date = State()
    selecting_time = State()
    entering_guests = State()
    confirming = State()


class AdminStates(StatesGroup):
    managing_rooms = State()
    managing_services = State()
    managing_bookings = State()
    adding_service = State()
    editing_service = State()
    adding_admin = State()
    removing_admin = State()


class PaymentStates(StatesGroup):
    selecting_payment_method = State()
    processing_payment = State()
    confirming_payment = State()


# ============= Обработчики команд для обновленной клавиатуры =============

@services_router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Показывает обновленное главное меню"""
    await message.answer(
        "Выберите действие из меню:",
        reply_markup=updated_main_keyboard()
    )


# ============= Обработчики для дополнительных услуг =============

@services_router.message(F.text == "🏊‍♂️ Дополнительные услуги")
async def show_services(message: Message, session: AsyncSession):
    """Показывает список доступных дополнительных услуг"""
    services = await get_available_services(session)

    if not services:
        await message.answer(
            "В данный момент дополнительные услуги недоступны. "
            "Пожалуйста, уточните информацию у администратора курорта.",
            reply_markup=updated_main_keyboard()
        )
        return

    await message.answer(
        "🏊‍♂️ *Дополнительные услуги*\n\n"
        "Выберите услугу для получения подробной информации и бронирования:",
        reply_markup=services_keyboard(services),
        parse_mode="Markdown"
    )


@services_router.callback_query(lambda c: c.data and c.data.startswith("service_"))
async def service_details(callback: CallbackQuery, session: AsyncSession):
    """Показывает детальную информацию о выбранной услуге"""
    service_id = int(callback.data.split("_")[1])
    service = await get_service(session, service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    # Формируем подробное описание услуги
    if service.is_hourly:
        price_text = f"{service.price:,.0f} сум/час"
    else:
        price_text = f"{service.price:,.0f} сум"

    capacity_text = f"Максимальное количество человек: {service.max_capacity}" if service.max_capacity else ""

    text = (
        f"🏊‍♂️ *{service.name}*\n\n"
        f"{service.description or 'Нет описания'}\n\n"
        f"💰 Стоимость: {price_text}\n"
        f"{capacity_text}\n\n"
        f"Для бронирования нажмите кнопку ниже."
    )

    # Отправляем информацию с клавиатурой
    if service.image_url:
        await callback.message.answer_photo(
            photo=service.image_url,
            caption=text,
            reply_markup=service_detail_keyboard(service.id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            text=text,
            reply_markup=service_detail_keyboard(service.id),
            parse_mode="Markdown"
        )

    await callback.answer()


@services_router.callback_query(lambda c: c.data and c.data.startswith("book_service_"))
async def start_service_booking(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начинает процесс бронирования дополнительной услуги"""
    service_id = int(callback.data.split("_")[2])
    service = await get_service(session, service_id)

    if not service:
        await callback.answer("Услуга не найдена")
        return

    # Сохраняем ID услуги в состоянии
    await state.update_data(service_id=service_id, service_name=service.name)

    # Предлагаем выбрать дату
    today = datetime.now().date()
    calendar_date = today

    await callback.message.answer(
        f"Выберите дату для бронирования услуги *{service.name}*:",
        reply_markup=calendar_keyboard(calendar_date),
        parse_mode="Markdown"
    )

    await state.set_state(ServiceBookingStates.selecting_date)
    await callback.answer()


@services_router.callback_query(lambda c: c.data and c.data.startswith("calendar_"),
                                ServiceBookingStates.selecting_date)
async def process_calendar_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обрабатывает выбор даты в календаре"""
    action = callback.data.split("_")[1]

    if action == "day":
        # Выбран день
        selected_date = callback.data.split("_")[2]
        await state.update_data(selected_date=selected_date)

        # Предлагаем выбрать время
        data = await state.get_data()
        service_id = data.get("service_id")
        service = await get_service(session, service_id)

        # Получаем доступные временные слоты для выбранной даты
        available_slots = []
        start_hour = 9  # 9:00
        end_hour = 21  # 21:00
        slot_duration = 1  # 1 час

        current_hour = start_hour
        while current_hour < end_hour:
            start_time = f"{current_hour:02d}:00"
            end_time = f"{current_hour + slot_duration:02d}:00"

            # Проверяем доступность слота
            is_available = await check_service_availability(
                session, service_id, selected_date, start_time, end_time
            )

            if is_available:
                available_slots.append((start_time, end_time))

            current_hour += slot_duration

        if not available_slots:
            await callback.message.answer(
                f"К сожалению, на выбранную дату ({selected_date}) нет доступных слотов для бронирования.\n"
                f"Пожалуйста, выберите другую дату.",
                reply_markup=calendar_keyboard(datetime.strptime(selected_date, "%Y-%m-%d").date())
            )
            return

        await callback.message.answer(
            f"Выберите время для бронирования услуги *{service.name}*:\n"
            f"Дата: {selected_date}",
            reply_markup=service_booking_keyboard(available_slots),
            parse_mode="Markdown"
        )

        await state.set_state(ServiceBookingStates.selecting_time)

    elif action == "next" or action == "prev":
        # Переход к следующему/предыдущему месяцу
        current_date = callback.data.split("_")[2]
        year, month = map(int, current_date.split("-"))

        if action == "next":
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
        else:
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1

        new_date = datetime(year, month, 1).date()
        await callback.message.edit_reply_markup(
            reply_markup=calendar_keyboard(new_date)
        )

    await callback.answer()


@services_router.callback_query(lambda c: c.data and c.data.startswith("time_"),
                                ServiceBookingStates.selecting_time)
async def process_time_selection(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обрабатывает выбор времени бронирования"""
    time_data = callback.data.split("_")[1:]
    start_time = time_data[0]
    end_time = time_data[1]

    await state.update_data(start_time=start_time, end_time=end_time)

    # Получаем информацию об услуге
    data = await state.get_data()
    service_id = data.get("service_id")
    service = await get_service(session, service_id)

    # Запрашиваем количество гостей
    max_guests_text = f" (максимум {service.max_capacity})" if service.max_capacity else ""

    await callback.message.answer(
        f"Введите количество человек для услуги *{service.name}*{max_guests_text}:",
        parse_mode="Markdown"
    )

    await state.set_state(ServiceBookingStates.entering_guests)
    await callback.answer()


@services_router.message(ServiceBookingStates.entering_guests)
async def process_guests_count(message: Message, state: FSMContext, session: AsyncSession):
    """Обрабатывает ввод количества гостей"""
    try:
        guests = int(message.text.strip())
        if guests <= 0:
            raise ValueError("Количество гостей должно быть положительным числом")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число гостей (целое положительное число).")
        return

    # Получаем информацию об услуге
    data = await state.get_data()
    service_id = data.get("service_id")
    service = await get_service(session, service_id)

    # Проверяем ограничение по количеству гостей
    if service.max_capacity and guests > service.max_capacity:
        await message.answer(
            f"Максимальное количество гостей для этой услуги: {service.max_capacity}.\n"
            f"Пожалуйста, введите корректное число."
        )
        return

    # Сохраняем количество гостей
    await state.update_data(guests=guests)

    # Суммируем всю информацию для подтверждения
    data = await state.get_data()
    selected_date = data.get("selected_date")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    # Рассчитываем стоимость
    if service.is_hourly:
        # Переводим время в часы
        start_hour = int(start_time.split(":")[0])
        end_hour = int(end_time.split(":")[0])
        duration_hours = end_hour - start_hour
        price = service.price * duration_hours
    else:
        price = service.price

    # Формируем сообщение для подтверждения
    confirmation_text = (
        f"📋 *Подтверждение бронирования*\n\n"
        f"Услуга: *{service.name}*\n"
        f"Дата: {selected_date}\n"
        f"Время: с {start_time} до {end_time}\n"
        f"Количество человек: {guests}\n"
        f"Стоимость: {price:,.0f} сум\n\n"
        f"Подтвердите бронирование:"
    )

    await message.answer(
        confirmation_text,
        reply_markup=confirm_cancel_keyboard(),
        parse_mode="Markdown"
    )

    await state.set_state(ServiceBookingStates.confirming)


@services_router.callback_query(F.data == "confirm", ServiceBookingStates.confirming)
async def confirm_service_booking(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждает бронирование услуги"""
    # Получаем все данные из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    selected_date = data.get("selected_date")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    guests = data.get("guests")

    # Получаем информацию о пользователе
    user = await get_or_create_user(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )

    try:
        # Создаем бронирование услуги
        service_booking = await create_service_booking(
            session,
            user_id=user.id,
            service_id=service_id,
            date=selected_date,
            start_time=start_time,
            end_time=end_time,
            guests=guests
        )

        # Отправляем подтверждение
        await callback.message.answer(
            f"✅ Бронирование успешно создано!\n\n"
            f"Номер бронирования: #{service_booking.id}\n"
            f"Услуга: {data.get('service_name')}\n"
            f"Дата: {selected_date}\n"
            f"Время: с {start_time} до {end_time}\n"
            f"Сумма: {service_booking.total_price:,.0f} сум\n\n"
            f"Статус: Ожидает подтверждения\n\n"
            f"С вами свяжется администратор для подтверждения бронирования.",
            reply_markup=payment_methods_keyboard(service_booking.id, "service")
        )

        # Очищаем состояние
        await state.clear()

    except ValueError as e:
        await callback.message.answer(
            f"❌ Ошибка при создании бронирования: {str(e)}\n"
            f"Пожалуйста, попробуйте выбрать другое время или дату.",
            reply_markup=updated_main_keyboard()
        )
        await state.clear()

    await callback.answer()


@services_router.callback_query(F.data == "cancel", ServiceBookingStates.confirming)
async def cancel_booking_process(callback: CallbackQuery, state: FSMContext):
    """Отменяет процесс бронирования"""
    await callback.message.answer(
        "❌ Бронирование отменено. Вы можете попробовать снова или вернуться в главное меню.",
        reply_markup=updated_main_keyboard()
    )
    await state.clear()
    await callback.answer()


@services_router.callback_query(F.data == "back_to_services")
async def back_to_services_list(callback: CallbackQuery, session: AsyncSession):
    """Возвращает к списку дополнительных услуг"""
    services = await get_available_services(session)

    await callback.message.answer(
        "🏊‍♂️ *Дополнительные услуги*\n\n"
        "Выберите услугу для получения подробной информации и бронирования:",
        reply_markup=services_keyboard(services),
        parse_mode="Markdown"
    )

    await callback.answer()


@services_router.message(F.text == "📅 Мои бронирования")
async def show_user_bookings(message: Message, session: AsyncSession):
    """Показывает список всех бронирований пользователя (номера и услуги)"""
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer(
            "Вы еще не зарегистрированы в системе. Пожалуйста, используйте команду /start для регистрации.",
            reply_markup=updated_main_keyboard()
        )
        return

    # Получаем бронирования номеров
    from app.database.crud import get_user_bookings
    room_bookings = await get_user_bookings(session, user.id)

    # Получаем бронирования услуг
    service_bookings = await get_user_service_bookings(session, user.id)

    # Если нет бронирований
    if not room_bookings and not service_bookings:
        await message.answer(
            "У вас пока нет активных бронирований.",
            reply_markup=updated_main_keyboard()
        )
        return

    # Формируем сообщение о бронированиях номеров
    message_text = "📅 *Ваши бронирования*\n\n"

    if room_bookings:
        message_text += "*Номера:*\n"
        for booking in room_bookings:
            status_emoji = "✅" if booking.status == "confirmed" else "⏳" if booking.status == "pending" else "❌"
            message_text += (
                f"{status_emoji} {booking.room.name} #{booking.id}\n"
                f"  📅 {booking.check_in.strftime('%d.%m.%Y')} - {booking.check_out.strftime('%d.%m.%Y')}\n"
                f"  👥 {booking.guests} чел., 💰 {booking.total_price:,.0f} сум\n"
                f"  Статус: {booking.status}\n\n"
            )

    # Добавляем информацию о бронированиях услуг
    if service_bookings:
        message_text += "*Дополнительные услуги:*\n"
        for booking in service_bookings:
            if booking.status == "cancelled":
                continue  # Пропускаем отмененные бронирования

            status_emoji = "✅" if booking.status == "confirmed" else "⏳" if booking.status == "pending" else "❌"
            message_text += (
                f"{status_emoji} {booking.service.name} #{booking.id}\n"
                f"  📅 {booking.date.strftime('%d.%m.%Y')}, "
                f"⏰ {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}\n"
                f"  👥 {booking.guests} чел., 💰 {booking.total_price:,.0f} сум\n"
                f"  Статус: {booking.status}\n\n"
            )

    # Отправляем сообщение с информацией о бронированиях
    await message.answer(message_text, parse_mode="Markdown")


# ============= Обработчики для административной панели =============

@admin_router.message(Command("admin"))
async def admin_panel(message: Message, session: AsyncSession):
    """Показывает административную панель, если пользователь является администратором"""
    admin = await get_bot_admin(session, message.from_user.id)

    if not admin:
        await message.answer("У вас нет доступа к административной панели.")
        return

    admin_text = (
        f"👨‍💼 *Административная панель*\n\n"
        f"Добро пожаловать, {message.from_user.first_name}!\n\n"
        f"Выберите раздел для управления:"
    )

    await message.answer(
        admin_text,
        reply_markup=admin_keyboard(admin),
        parse_mode="Markdown"
    )


@admin_router.callback_query(lambda c: c.data and c.data == "admin_rooms")
async def admin_manage_rooms(callback: CallbackQuery, session: AsyncSession):
    """Управление номерами"""
    admin = await get_bot_admin(session, callback.from_user.id)

    if not admin or not admin.can_manage_rooms:
        await callback.answer("У вас нет доступа к этому разделу")
        return

    await callback.message.answer(
        "🛏️ *Управление номерами*\n\n"
        "Здесь вы можете просматривать, добавлять и редактировать номера, "
        "а также управлять их доступностью.\n\n"
        "Выберите действие:",
        reply_markup=room_availability_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.callback_query(lambda c: c.data and c.data == "admin_services")
async def admin_manage_services(callback: CallbackQuery, session: AsyncSession):
    """Управление дополнительными услугами"""
    admin = await get_bot_admin(session, callback.from_user.id)

    if not admin or not admin.can_manage_services:
        await callback.answer("У вас нет доступа к этому разделу")
        return

    services = await get_all_services(session)

    await callback.message.answer(
        "🏊‍♂️ *Управление дополнительными услугами*\n\n"
        "Здесь вы можете просматривать, добавлять, редактировать и удалять дополнительные услуги.\n\n"
        "Выберите услугу или действие:",
        reply_markup=services_keyboard(services, is_admin=True),
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.callback_query(lambda c: c.data and c.data == "admin_bookings")
async def admin_manage_bookings(callback: CallbackQuery, session: AsyncSession):
    """Управление бронированиями"""
    admin = await get_bot_admin(session, callback.from_user.id)

    if not admin or not admin.can_manage_bookings:
        await callback.answer("У вас нет доступа к этому разделу")
        return

    await callback.message.answer(
        "📝 *Управление бронированиями*\n\n"
        "Здесь вы можете просматривать и управлять бронированиями номеров и услуг.\n\n"
        "Выберите действие:",
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.callback_query(lambda c: c.data and c.data == "room_calendar")
async def show_room_calendar(callback: CallbackQuery, session: AsyncSession):
    """Показывает календарь занятости номеров"""
    admin = await get_bot_admin(session, callback.from_user.id)

    if not admin or not admin.can_manage_rooms:
        await callback.answer("У вас нет доступа к этой функции")
        return

    # Получаем данные о занятости номеров на ближайший месяц
    today = datetime.now().date()
    next_month = today + timedelta(days=30)

    occupancy = await get_all_rooms_occupancy(
        session,
        today.strftime("%Y-%m-%d"),
        next_month.strftime("%Y-%m-%d")
    )

    # Формируем сообщение с информацией о занятости
    message_text = "📅 *Календарь занятости номеров*\n\n"

    from app.database.crud import get_all_rooms
    rooms = await get_all_rooms(session)

    for room in rooms:
        room_occupancy = occupancy.get(room.id, [])
        message_text += f"*{room.name}:*\n"

        if not room_occupancy:
            message_text += "  Свободен на ближайший месяц\n\n"
            continue

        for booking in room_occupancy:
            message_text += (
                f"  • {booking['check_in']} - {booking['check_out']}\n"
                f"    {booking['guest_name']}, {booking['guests']} чел.\n"
            )

        message_text += "\n"

    await callback.message.answer(
        message_text,
        parse_mode="Markdown"
    )
    await callback.answer()


@admin_router.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: CallbackQuery, session: AsyncSession):
    """Возвращает к административной панели"""
    admin = await get_bot_admin(session, callback.from_user.id)

    if not admin:
        await callback.answer("У вас нет доступа к административной панели")
        return

    admin_text = (
        f"👨‍💼 *Административная панель*\n\n"
        f"Добро пожаловать, {callback.from_user.first_name}!\n\n"
        f"Выберите раздел для управления:"
    )

    await callback.message.answer(
        admin_text,
        reply_markup=admin_keyboard(admin),
        parse_mode="Markdown"
    )
    await callback.answer()


# ============= Обработчики для платежей =============

@payment_router.callback_query(lambda c: c.data and c.data.startswith("pay_"))
async def start_payment_process(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начинает процесс оплаты"""
    # Формат data: pay_<type>_<id>_<method>
    # type: booking или service
    # id: ID бронирования
    # method: payme, click или cash
    parts = callback.data.split("_")

    if len(parts) < 4:
        await callback.answer("Некорректный формат данных")
        return

    booking_type = parts[1]
    booking_id = int(parts[2])
    payment_method = parts[3]

    # Получаем данные о бронировании
    if booking_type == "booking":
        from app.database.crud import get_booking
        booking = await get_booking(session, booking_id)
        if not booking:
            await callback.answer("Бронирование не найдено")
            return

        amount = booking.total_price
        service_booking_id = None
        description = f"Оплата бронирования номера #{booking_id}"

    elif booking_type == "service":
        service_booking = await get_service_booking(session, booking_id)
        if not service_booking:
            await callback.answer("Бронирование услуги не найдено")
            return

        amount = service_booking.total_price
        booking_id = None
        service_booking_id = service_booking.id
        description = f"Оплата бронирования услуги {service_booking.service.name} #{service_booking_id}"

    else:
        await callback.answer("Некорректный тип бронирования")
        return

    # Обработка различных методов оплаты
    if payment_method == "cash":
        # Создаем запись о платеже с методом оплаты "cash"
        payment = await create_payment(
            session,
            amount=amount,
            payment_method="cash",
            booking_id=booking_id,
            service_booking_id=service_booking_id,
            details={"description": description, "payment_type": "cash"}
        )

        await callback.message.answer(
            f"✅ Выбрана оплата при заселении\n\n"
            f"Ваше бронирование подтверждено. Оплата будет произведена при заселении.\n"
            f"Номер платежа: #{payment.id}\n"
            f"Сумма: {amount:,.0f} сум",
            reply_markup=updated_main_keyboard()
        )

    elif payment_method in ["payme", "click"]:
        # Создаем запись о платеже
        payment = await create_payment(
            session,
            amount=amount,
            payment_method=payment_method,
            booking_id=booking_id,
            service_booking_id=service_booking_id,
            details={"description": description, "payment_type": "online"}
        )

        # Формируем сообщение с инструкцией по оплате
        payment_instructions = (
            f"💳 *Инструкция по оплате через {payment_method.upper()}*\n\n"
            f"1. Отсканируйте QR-код или нажмите на ссылку ниже\n"
            f"2. Введите сумму: {amount:,.0f} сум\n"
            f"3. В комментарии укажите номер бронирования: "
            f"{'B' if booking_id else 'S'}{booking_id or service_booking_id}\n\n"
            f"После оплаты, пожалуйста, пришлите чек или скриншот оплаты администратору."
        )

        await callback.message.answer(
            payment_instructions,
            parse_mode="Markdown"
        )

        # Здесь можно добавить логику для генерации QR-кода или ссылки на оплату
        # В данном примере просто показываем инструкцию

    else:
        await callback.answer("Неизвестный метод оплаты")
        return

    await callback.answer()

    # Регистрация всех обработчиков в одной функции
    def register_additional_handlers(dispatcher):
        """Регистрирует все дополнительные обработчики"""
        dispatcher.include_router(services_router)
        dispatcher.include_router(admin_router)
        dispatcher.include_router(calendar_router)
        dispatcher.include_router(payment_router)