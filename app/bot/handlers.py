from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.singleton_router import get_router
from app.bot.keyboards import main_keyboard, rooms_keyboard, room_detail_keyboard, support_keyboard
from app.database.crud import (
    get_user_by_telegram_id, create_user, get_all_rooms,
    get_room, get_room_reviews, get_or_create_user
)
from app.database.models import User
from app.config import RESORT_PHONE, RESORT_ADMIN_USERNAME, RESORT_NAME, RESORT_LOCATION, RESORT_ALTITUDE

# Get the singleton router instance
router = get_router()


# Handler for /start command
@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession):
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


# Handler for room selection
@router.callback_query(lambda c: c.data and c.data.startswith("room_"))
async def room_details(callback: CallbackQuery, session: AsyncSession):
    room_id = int(callback.data.split("_")[1])
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

    # Формат цены: добавляем разные цены для будних и выходных
    price_text = f"{room.price_per_night}сум"

    # Добавляем цену выходного дня, если она есть
    if hasattr(room, "weekend_price") and room.weekend_price:
        price_text = f"{room.price_per_night}сум (ПН-ЧТ) / {room.weekend_price}сум (ПТ-ВС)"

    # Определяем, что включено в номер
    included_text = ""
    if room.room_type != "tapchan":  # Для всех кроме тапчанов
        included_text = "Включено:\n"
        if hasattr(room, "with_breakfast") and room.with_breakfast:
            included_text += "- Завтрак\n"
        included_text += "- 1 час детская площадка\n"
    else:  # Для тапчанов
        included_text = "Доступно дополнительно:\n- Мангал (по запросу)\n"

    # Create room description text без специальных символов Markdown
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

    # Send photo with room if image exists
    if room.image_url:
        await callback.message.answer_photo(
            photo=room.image_url,
            caption=text,
            reply_markup=room_detail_keyboard(room.id),
            parse_mode=None  # Отключаем Markdown
        )
    else:
        await callback.message.answer(
            text=text,
            reply_markup=room_detail_keyboard(room.id),
            parse_mode=None  # Отключаем Markdown
        )

    await callback.answer()


# Handler for "Contact Support" button
@router.message(F.text == "📞 Связь с поддержкой")
async def contact_support(message: Message):
    await message.answer(
        "📞 Связь с поддержкой\n\n"
        "Если у вас возникли вопросы или вам нужна помощь, вы можете связаться с нами одним из следующих способов:\n\n"
        f"☎️ Телефон: {RESORT_PHONE}\n"
        f"✉️ Telegram: @{RESORT_ADMIN_USERNAME}",
        reply_markup=support_keyboard(),
        parse_mode=None  # Отключаем Markdown
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
        parse_mode=None  # Отключаем Markdown
    )
    await callback.answer()


# Handler for "Reviews" button
@router.message(F.text == "⭐ Отзывы")
async def show_reviews(message: Message, session: AsyncSession):
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
        parse_mode=None  # Отключаем Markdown
    )
    await callback.answer()


# Handler for unknown messages
@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "Я не понимаю эту команду. Пожалуйста, воспользуйтесь меню.",
        reply_markup=main_keyboard()
    )