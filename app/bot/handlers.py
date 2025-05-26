from aiogram import F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import calendar
from datetime import datetime, timedelta
import json
import logging

from app.bot.singleton_router import get_router
from app.bot.keyboards import main_keyboard, rooms_keyboard, room_detail_keyboard, support_keyboard
from app.database.crud import (
    get_user_by_telegram_id, create_user, get_all_rooms,
    get_room, get_room_reviews, get_or_create_user, check_room_availability
)
from app.database.models import User
from app.config import RESORT_PHONE, RESORT_ADMIN_USERNAME, RESORT_NAME, RESORT_LOCATION, RESORT_ALTITUDE, WEBAPP_URL

# Настройка логирования
logger = logging.getLogger(__name__)

# Get the singleton router instance
router = get_router()


# Handler for /start command
@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
    logger.info(f"Start command from user {message.from_user.id}")

    # Check if user exists in the database or create a new one
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        f"Добро пожаловать в бот курорта «{RESORT_NAME}».\n\n"
        f"Здесь вы можете узнать информацию о нашем курорте, посмотреть номера, "
        f"забронировать проживание, а также связаться с нашей поддержкой.",
        reply_markup=main_keyboard()
    )


# Handler for "About Resort" button
@router.message(F.text == "🏨 О курорте")
async def about_resort(message: Message):
    logger.info(f"About resort from user {message.from_user.id}")

    await message.answer(
        f"🏨 Курорт «{RESORT_NAME}»\n\n"
        f"Наш курорт расположен в живописном горном ущелье, в 120 км от города Ташкент.\n\n"
        f"📍 Расположение: {RESORT_LOCATION}\n"
        f"🏔 Высота над уровнем моря: {RESORT_ALTITUDE}\n"
        f"🌡 Климат: Горный, умеренный\n\n"
        f"На территории курорта:\n"
        f"- Открытый и закрытый бассейны\n"
        f"- Ресторан с национальной и европейской кухней\n"
        f"- SPA-центр\n"
        f"- Детская площадка\n"
        f"- Зоны для пикника\n\n"
        f"Мы работаем круглый год и предлагаем различные виды отдыха в зависимости от сезона.",
        parse_mode=None
    )


# Handler for "Rooms" button
@router.message(F.text == "🛏️ Номера")
async def show_rooms(message: Message, session: AsyncSession):
    logger.info(f"Show rooms from user {message.from_user.id}")

    # Get rooms with await
    rooms = await get_all_rooms(session)

    await message.answer(
        "🛏️ Выберите категорию номера для подробной информации:",
        reply_markup=rooms_keyboard(rooms),
        parse_mode=None
    )


# Handler для групп номеров
@router.callback_query(lambda c: c.data and c.data.startswith("room_type_"))
async def room_type_info(callback: CallbackQuery, session: AsyncSession):
    logger.info(f"Room type info: {callback.data}")

    room_type = callback.data.split("_")[2]

    # Описания для разных типов номеров
    type_descriptions = {
        "standard": "Стандартные номера предлагают комфортное размещение с основными удобствами для отличного отдыха.",
        "luxury": "Люкс номера отличаются повышенным комфортом и просторностью для требовательных гостей.",
        "vip": "VIP номера предлагают эксклюзивный сервис и дополнительные привилегии для особых гостей.",
        "apartment": "Апартаменты включают кухонную зону и отдельную гостиную для более длительного и комфортного проживания.",
        "cottage": "Коттеджи представляют собой отдельно стоящие домики с собственной территорией для максимальной приватности.",
        "president": "Президентские апартаменты - самое роскошное размещение с максимальным уровнем сервиса и комфорта.",
        "tapchan": "Тапчаны - традиционные зоны отдыха под открытым небом для дневного отдыха компанией."
    }

    # Текст для каждого типа
    if room_type in type_descriptions:
        await callback.message.answer(
            f"ℹ️ {type_descriptions[room_type]}\n\n"
            f"Выберите конкретный номер для получения подробной информации и бронирования.",
            parse_mode=None
        )

    await callback.answer()


# Handler for room selection - ИСПРАВЛЕННЫЙ
@router.callback_query(lambda c: c.data and c.data.startswith("room_") and len(c.data.split("_")) == 2)
async def room_details(callback: CallbackQuery, session: AsyncSession):
    logger.info(f"Room details: {callback.data}")

    try:
        room_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка обработки запроса")
        return

    room = await get_room(session, room_id)

    if not room:
        await callback.answer("Номер не найден")
        return

    # Определяем тип номера на русском
    room_type_names = {
        "standard": "Стандартный",
        "luxury": "Люкс",
        "vip": "VIP",
        "apartment": "Апартамент",
        "cottage": "Коттедж",
        "president": "Президентский",
        "tapchan": "Тапчан"
    }

    room_type_ru = room_type_names.get(room.room_type, room.room_type)

    # Формат цены
    if hasattr(room, "weekend_price") and room.weekend_price and room.weekend_price != room.price_per_night:
        price_text = f"{room.price_per_night:,.0f} сум (ПН-ЧТ) / {room.weekend_price:,.0f} сум (ПТ-ВС)"
    else:
        price_text = f"{room.price_per_night:,.0f} сум"

    # Определяем, что включено
    included_text = ""
    if room.room_type != "tapchan":
        included_text = "Включено:\n"
        if hasattr(room, "with_breakfast") and room.with_breakfast:
            included_text += "- Завтрак\n"
        included_text += "- 1 час детская площадка\n"
    else:
        included_text = "Доступно дополнительно:\n- Мангал (по запросу)\n"

    # Проверяем наличие видео
    has_video = hasattr(room, 'video_url') and room.video_url is not None

    # Создаем текст описания
    text = (
        f"🛏️ {room.name}\n\n"
        f"Тип: {room_type_ru}\n"
        f"Вместимость: {room.capacity} чел.\n"
        f"Цена: {price_text}\n\n"
        f"{room.description}\n\n"
        f"{included_text}\n"
        f"Время заезда: 14:00\n"
        f"Время выезда: 12:00\n\n"
        f"Для бронирования нажмите кнопку ниже."
    )

    # Отправляем фото с описанием
    if room.image_url:
        await callback.message.answer_photo(
            photo=room.image_url,
            caption=text,
            reply_markup=room_detail_keyboard(room.id, has_video=has_video),
            parse_mode=None
        )
    else:
        await callback.message.answer(
            text=text,
            reply_markup=room_detail_keyboard(room.id, has_video=has_video),
            parse_mode=None
        )

    await callback.answer()


# Handler for "Contact Support" button
@router.message(F.text == "📞 Связь с поддержкой")
async def contact_support(message: Message):
    logger.info(f"Contact support from user {message.from_user.id}")

    await message.answer(
        "📞 Связь с поддержкой\n\n"
        "Если у вас возникли вопросы или вам нужна помощь, вы можете связаться с нами одним из следующих способов:\n\n"
        f"☎️ Телефон: {RESORT_PHONE}\n"
        f"✉️ Telegram: @{RESORT_ADMIN_USERNAME}",
        reply_markup=support_keyboard(),
        parse_mode=None
    )


# Handler for phone number display
@router.callback_query(F.data == "phone_number")
async def show_phone_number(callback: CallbackQuery):
    await callback.answer(f"Телефон администратора: {RESORT_PHONE}")


@router.callback_query(F.data == "call_support")
async def call_support(callback: CallbackQuery):
    await callback.message.answer(
        "📞 Позвонить администратору\n\n"
        "Вы можете позвонить нам по номеру:\n"
        f"{RESORT_PHONE}\n\n"
        "Часы работы: 9:00 - 18:00 (ПН-СБ)",
        parse_mode=None
    )
    await callback.answer()


# Handler for "Reviews" button
@router.message(F.text == "⭐ Отзывы")
async def show_reviews(message: Message, session: AsyncSession):
    logger.info(f"Show reviews from user {message.from_user.id}")

    await message.answer(
        "⭐ Отзывы о курорте\n\n"
        "Здесь вы можете прочитать отзывы наших гостей или оставить свой отзыв.\n\n"
        "Чтобы оставить отзыв, пожалуйста, воспользуйтесь нашим веб-приложением или напишите отзыв напрямую боту.",
        parse_mode=None
    )


# Handler for returning to main menu
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=main_keyboard()
    )
    await callback.message.delete()
    await callback.answer()


# Handler for returning to rooms list
@router.callback_query(F.data == "back_to_rooms")
async def back_to_rooms(callback: CallbackQuery, session: AsyncSession):
    rooms = await get_all_rooms(session)
    await callback.message.answer(
        "🛏️ Выберите категорию номера для подробной информации:",
        reply_markup=rooms_keyboard(rooms),
        parse_mode=None
    )
    await callback.message.delete()
    await callback.answer()


# Handler for room reviews
@router.callback_query(lambda c: c.data and c.data.startswith("reviews_"))
async def room_reviews(callback: CallbackQuery, session: AsyncSession):
    room_id = int(callback.data.split("_")[1])
    reviews = await get_room_reviews(session, room_id)
    room = await get_room(session, room_id)

    if not reviews:
        text = f"⭐ Отзывы о номере \"{room.name}\"\n\nПока нет отзывов об этом номере."
    else:
        text = f"⭐ Отзывы о номере \"{room.name}\"\n\n"
        for review in reviews:
            stars = "⭐" * review.rating
            text += f"{stars}\n{review.comment}\n\n"

    await callback.message.answer(
        text,
        reply_markup=room_detail_keyboard(room_id),
        parse_mode=None
    )
    await callback.answer()


# =================== ВИДЕО ФУНКЦИИ ===================

# Handler для видео-туров - ИСПРАВЛЕННАЯ ВЕРСИЯ
@router.callback_query(lambda c: c.data and c.data.startswith("video_tour_"))
async def show_video_tour(callback: CallbackQuery, session: AsyncSession):
    logger.info(f"Video tour: {callback.data}")

    room_id = int(callback.data.split("_")[2])
    room = await get_room(session, room_id)

    if not room:
        await callback.answer("Номер не найден")
        return

    # Проверяем наличие видео URL
    if not hasattr(room, 'video_url') or not room.video_url:
        # Если видео нет, показываем сообщение
        await callback.message.answer(
            f"🎥 Видео-тур для номера \"{room.name}\" временно недоступен.\n\n"
            f"Вы можете посмотреть фотографии номера или связаться с нами для виртуальной экскурсии.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📸 Смотреть фото", callback_data=f"all_photos_{room_id}")],
                [InlineKeyboardButton(text="📞 Связаться", callback_data="call_support")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"room_{room_id}")]
            ])
        )
        await callback.answer("Видео временно недоступно")
        return

    # Если видео есть - отправляем ссылку
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Смотреть видео", url=room.video_url)],
        [InlineKeyboardButton(text="🔙 Назад к номеру", callback_data=f"room_{room_id}")]
    ])

    await callback.message.answer(
        f"🎥 Видео-тур: {room.name}\n\n"
        f"Нажмите кнопку ниже, чтобы посмотреть видео-обзор номера.",
        reply_markup=keyboard
    )
    await callback.answer()


# Добавим в главное меню новую кнопку
@router.message(F.text == "🎥 Виртуальные туры")
async def virtual_tours_menu(message: Message):
    logger.info(f"Virtual tours from user {message.from_user.id}")

    # Временные ссылки на демо-контент
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏞 Обзор территории",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Замените на реальное видео
        )],
        [InlineKeyboardButton(
            text="🏊 Зона бассейна",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Замените на реальное видео
        )],
        [InlineKeyboardButton(
            text="🍽 Ресторан",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Замените на реальное видео
        )],
        [InlineKeyboardButton(
            text="🏠 Виртуальный тур 360°",
            url="https://www.google.com/maps/@41.2995,69.2401,3a,75y,90t/data=!3m6!1e1!3m4!1s0x0:0x0!2e0!7i13312!8i6656"
            # Пример
        )],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]
    ])

    await message.answer(
        "🎥 Виртуальные туры по курорту Oqtoshsoy\n\n"
        "Выберите, что хотите посмотреть:\n"
        "Видео откроются в браузере.",
        reply_markup=keyboard,
        parse_mode=None
    )


# Handler для показа всех фото номера
@router.callback_query(lambda c: c.data and c.data.startswith("all_photos_"))
async def show_all_photos(callback: CallbackQuery, session: AsyncSession):
    logger.info(f"All photos: {callback.data}")

    room_id = int(callback.data.split("_")[2])
    room = await get_room(session, room_id)

    if not room:
        await callback.answer("Номер не найден")
        return

    # Парсим JSON с фотографиями
    photos = []
    if room.photos:
        try:
            photos = json.loads(room.photos)
        except:
            photos = []

    if photos:
        # Отправляем альбом фотографий
        media_group = []
        for i, photo_url in enumerate(photos[:10]):  # Максимум 10 фото в альбоме
            media_group.append(
                InputMediaPhoto(
                    media=photo_url,
                    caption=f"{room.name} - фото {i + 1}" if i == 0 else None
                )
            )

        await callback.message.answer_media_group(media_group)

        # Если фото больше 10, сообщаем об этом
        if len(photos) > 10:
            await callback.message.answer(
                f"Показаны первые 10 фото из {len(photos)}.\n"
                f"Все фотографии доступны в нашем веб-приложении.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📸 Смотреть все фото",
                        web_app=WebAppInfo(url=f"{WEBAPP_URL}?room_id={room_id}&tab=photos")
                    )],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data=f"room_{room_id}")]
                ])
            )
    else:
        await callback.message.answer(
            "Дополнительные фотографии пока не загружены.",
            reply_markup=room_detail_keyboard(room_id)
        )

    await callback.answer()


# =================== БЫСТРОЕ БРОНИРОВАНИЕ ===================

# Генератор календаря для выбора дат
def generate_calendar_keyboard(year: int, month: int, selected_dates: list = None):
    if selected_dates is None:
        selected_dates = []

    keyboard = []

    # Заголовок с месяцем и годом
    month_name = calendar.month_name[month]
    header = [InlineKeyboardButton(
        text=f"{month_name} {year}",
        callback_data="ignore"
    )]
    keyboard.append(header)

    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data="ignore")
        for day in week_days
    ])

    # Календарь
    cal = calendar.monthcalendar(year, month)
    today = datetime.now().date()

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date = datetime(year, month, day).date()

                # Проверяем, не прошедшая ли это дата
                if date < today:
                    row.append(InlineKeyboardButton(
                        text=f"·{day}·",
                        callback_data="ignore"
                    ))
                # Проверяем, выбрана ли дата
                elif date in selected_dates:
                    row.append(InlineKeyboardButton(
                        text=f"✅ {day}",
                        callback_data=f"unselect_date_{date.isoformat()}"
                    ))
                # Выходные дни подсвечиваем
                elif date.weekday() in [4, 5, 6]:  # Пт, Сб, Вс
                    row.append(InlineKeyboardButton(
                        text=f"🔴 {day}",
                        callback_data=f"select_date_{date.isoformat()}"
                    ))
                else:
                    row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"select_date_{date.isoformat()}"
                    ))
        keyboard.append(row)

    # Навигация
    nav_row = []
    if month > 1 or year > datetime.now().year:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"calendar_{year}_{month - 1 if month > 1 else 12}_{year if month > 1 else year - 1}"
        ))
    nav_row.append(InlineKeyboardButton(
        text="📅 Сегодня",
        callback_data=f"calendar_{datetime.now().year}_{datetime.now().month}_current"
    ))
    nav_row.append(InlineKeyboardButton(
        text="▶️",
        callback_data=f"calendar_{year}_{month + 1 if month < 12 else 1}_{year if month < 12 else year + 1}"
    ))
    keyboard.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Быстрое бронирование
@router.callback_query(lambda c: c.data and c.data.startswith("quick_book_"))
async def quick_booking(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    logger.info(f"Quick booking: {callback.data}")

    room_id = int(callback.data.split("_")[2])
    room = await get_room(session, room_id)

    if not room:
        await callback.answer("Номер не найден")
        return

    # Сохраняем выбранный номер в состоянии
    await state.update_data(room_id=room_id, room_name=room.name)

    # Показываем популярные варианты дат
    today = datetime.now().date()
    weekend = today + timedelta(days=(5 - today.weekday()) % 7)  # Ближайшая пятница

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚀 Сегодня-Завтра",
            callback_data=f"express_book_{room_id}_{today}_{today + timedelta(days=1)}"
        )],
        [InlineKeyboardButton(
            text="🎉 Ближайшие выходные",
            callback_data=f"express_book_{room_id}_{weekend}_{weekend + timedelta(days=2)}"
        )],
        [InlineKeyboardButton(
            text="📅 Выбрать даты в календаре",
            callback_data=f"calendar_book_{room_id}"
        )],
        [InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"room_{room_id}"
        )]
    ])

    await callback.message.answer(
        f"⚡ Быстрое бронирование\n\n"
        f"🛏 {room.name}\n"
        f"💰 {room.price_per_night:,.0f} сум/ночь (будни)\n"
        f"💰 {getattr(room, 'weekend_price', room.price_per_night):,.0f} сум/ночь (выходные)\n\n"
        f"Выберите вариант:",
        reply_markup=keyboard
    )
    await callback.answer()


# Экспресс-бронирование
@router.callback_query(lambda c: c.data and c.data.startswith("express_book_"))
async def express_booking(callback: CallbackQuery, session: AsyncSession):
    logger.info(f"Express booking: {callback.data}")

    parts = callback.data.split("_")
    room_id = int(parts[2])
    check_in = datetime.fromisoformat(parts[3]).date()
    check_out = datetime.fromisoformat(parts[4]).date()

    # Проверяем доступность
    is_available = await check_room_availability(
        session, room_id,
        check_in.isoformat(),
        check_out.isoformat()
    )

    if not is_available:
        await callback.answer("❌ К сожалению, номер занят на эти даты", show_alert=True)
        return

    # Рассчитываем стоимость
    room = await get_room(session, room_id)
    nights = (check_out - check_in).days

    # Считаем выходные дни
    weekend_nights = 0
    current = check_in
    while current < check_out:
        if current.weekday() in [4, 5, 6]:  # Пт, Сб, Вс
            weekend_nights += 1
        current += timedelta(days=1)

    weekday_nights = nights - weekend_nights

    # Используем getattr для безопасного доступа к weekend_price
    weekend_price = getattr(room, 'weekend_price', room.price_per_night)
    total_price = (weekday_nights * room.price_per_night) + (weekend_nights * weekend_price)

    # Отправляем в веб-приложение для завершения бронирования
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Завершить бронирование",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?room_id={room_id}&check_in={check_in}&check_out={check_out}")
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"room_{room_id}"
        )]
    ])

    await callback.message.answer(
        f"✅ Номер доступен!\n\n"
        f"📋 Детали бронирования:\n"
        f"🛏 {room.name}\n"
        f"📅 Заезд: {check_in.strftime('%d.%m.%Y')}\n"
        f"📅 Выезд: {check_out.strftime('%d.%m.%Y')}\n"
        f"🌙 Ночей: {nights} (будни: {weekday_nights}, выходные: {weekend_nights})\n"
        f"💰 Итого: {total_price:,.0f} сум\n\n"
        f"Нажмите кнопку ниже для завершения бронирования:",
        reply_markup=keyboard
    )
    await callback.answer()


# Handler for unknown messages
@router.message()
async def unknown_message(message: Message):
    logger.info(f"Unknown message from user {message.from_user.id}: {message.text}")

    await message.answer(
        "Я не понимаю эту команду. Пожалуйста, воспользуйтесь меню.",
        reply_markup=main_keyboard()
    )