from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_keyboard, rooms_keyboard, room_detail_keyboard, support_keyboard
from app.database.crud import (
    get_user_by_telegram_id, create_user, get_all_rooms,
    get_room, get_room_reviews, get_or_create_user
)
from app.database.models import User

router = Router()


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
        f"Добро пожаловать в бот курорта «Oqtoshsoy».\n\n"
        f"Здесь вы можете узнать информацию о нашем курорте, посмотреть номера, "
        f"забронировать проживание, а также связаться с нашей поддержкой.",
        reply_markup=main_keyboard()
    )


# Handler for "About Resort" button
@router.message(F.text == "🏨 О курорте")
async def about_resort(message: Message):
    await message.answer(
        "🏨 *Курорт «Oqtoshsoy»*\n\n"
        "Наш курорт расположен в живописном горном ущелье, в 120 км от города Ташкент.\n\n"
        "📍 *Расположение*: Ташкентская область, Бостанлыкский район\n"
        "🏔 *Высота над уровнем моря*: 1200 м\n"
        "🌡 *Климат*: Горный, умеренный\n\n"
        "На территории курорта:\n"
        "- Открытый и закрытый бассейны\n"
        "- Ресторан с национальной и европейской кухней\n"
        "- SPA-центр\n"
        "- Детская площадка\n"
        "- Зоны для пикника\n\n"
        "Мы работаем круглый год и предлагаем различные виды отдыха в зависимости от сезона.",
        parse_mode="Markdown"
    )


# Handler for "Rooms" button
@router.message(F.text == "🛏️ Номера")
async def show_rooms(message: Message, session: AsyncSession):
    # Get rooms with await
    rooms = await get_all_rooms(session)

    await message.answer(
        "🛏️ *Выберите категорию номера для подробной информации:*",
        reply_markup=rooms_keyboard(rooms),
        parse_mode="Markdown"
    )


# Handler for room selection
@router.callback_query(lambda c: c.data and c.data.startswith("room_"))
async def room_details(callback: CallbackQuery, session: AsyncSession):
    room_id = int(callback.data.split("_")[1])
    room = await get_room(session, room_id)

    if not room:
        await callback.answer("Номер не найден")
        return

    # Create room description text
    text = (
        f"🛏️ *{room.name}*\n\n"
        f"*Тип*: {room.room_type}\n"
        f"*Вместимость*: {room.capacity} чел.\n"
        f"*Цена за ночь*: {room.price_per_night}₽\n\n"  # Use price_per_night
        f"{room.description}\n\n"
        f"Для бронирования нажмите кнопку ниже."
    )

    # Send photo with room if image exists
    if room.image_url:
        await callback.message.answer_photo(
            photo=room.image_url,
            caption=text,
            reply_markup=room_detail_keyboard(room.id),
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            text=text,
            reply_markup=room_detail_keyboard(room.id),
            parse_mode="Markdown"
        )

    await callback.answer()


# Handler for "Contact Support" button
@router.message(F.text == "📞 Связь с поддержкой")
async def contact_support(message: Message):
    await message.answer(
        "📞 *Связь с поддержкой*\n\n"
        "Если у вас возникли вопросы или вам нужна помощь, вы можете связаться с нами одним из следующих способов:",
        reply_markup=support_keyboard(),
        parse_mode="Markdown"
    )


# Handler for "Reviews" button
@router.message(F.text == "⭐ Отзывы")
async def show_reviews(message: Message, session: AsyncSession):
    await message.answer(
        "⭐ *Отзывы о курорте*\n\n"
        "Здесь вы можете прочитать отзывы наших гостей или оставить свой отзыв.\n\n"
        "Чтобы оставить отзыв, пожалуйста, воспользуйтесь нашим веб-приложением или напишите отзыв напрямую боту.",
        parse_mode="Markdown"
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


# Handler for unknown messages
@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "Я не понимаю эту команду. Пожалуйста, воспользуйтесь меню.",
        reply_markup=main_keyboard()
    )