# app/bot/notifications.py

import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database.models import Booking, User
from app.config import BOT_TOKEN, ADMIN_TELEGRAM_ID
import logging
# 5. Обновите app/bot/notifications.py - используйте BatchMessageSender:
from app.bot.batch_sender import BatchMessageSender


async def send_reminder_24h(self, session: AsyncSession):
    """Отправка напоминаний за 24 часа до заезда"""
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)

    # Получаем все данные одним запросом
    result = await session.execute(
        select(Booking)
        .options(
            selectinload(Booking.user),
            selectinload(Booking.room)
        )
        .where(
            and_(
                Booking.check_in >= tomorrow_start,
                Booking.check_in <= tomorrow_end,
                Booking.status == "confirmed"
            )
        )
    )
    bookings = result.scalars().all()

    # Используем батч-отправку
    sender = BatchMessageSender(self.bot, batch_size=25, delay=0.1)

    for booking in bookings:
        text = (
            f"🔔 Напоминание о бронировании!\n\n"
            f"Завтра ваш заезд в курорт Oqtoshsoy:\n"
            f"🛏 Номер: {booking.room.name}\n"
            f"📅 Заезд: {booking.check_in.strftime('%d.%m.%Y')} в 14:00\n"
            f"📅 Выезд: {booking.check_out.strftime('%d.%m.%Y')} до 12:00\n\n"
            f"📍 Адрес: Ташкентская область, Бостанлыкский район\n"
            f"📞 Контакт: +998 90 096 50 55\n\n"
            f"Ждем вас с нетерпением! 🌟"
        )

        await sender.add_message(booking.user.telegram_id, text)

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для автоматических уведомлений"""

    def __init__(self, bot: Bot):
        for booking in bookings:
            try:
                await self.bot.send_message(
                    booking.user.telegram_id,
                    f"🌟 Как прошел ваш отдых?\n\n"
                    f"Надеемся, вам понравилось в курорте Oqtoshsoy!\n"
                    f"Поделитесь впечатлениями - ваш отзыв поможет нам стать лучше.\n\n"
                    f"Нажмите /review_{booking.id} чтобы оставить отзыв\n\n"
                    f"Или просто оцените от 1 до 5 ⭐",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="⭐", callback_data=f"rate_{booking.id}_1"),
                            InlineKeyboardButton(text="⭐⭐", callback_data=f"rate_{booking.id}_2"),
                            InlineKeyboardButton(text="⭐⭐⭐", callback_data=f"rate_{booking.id}_3"),
                            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"rate_{booking.id}_4"),
                            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"rate_{booking.id}_5")
                        ]
                    ])
                )
            except Exception as e:
                logger.error(f"Error sending review request for booking {booking.id}: {e}")

    async def send_special_offers(self, session: AsyncSession, offer_type: str):
        """Отправка специальных предложений подписчикам"""
        # Получаем всех пользователей с подпиской на акции
        result = await session.execute(
            select(User).where(User.subscribed_to_offers == True)
        )
        users = result.scalars().all()

        offers = {
            "weekend": {
                "title": "🎉 Скидка выходного дня!",
                "text": "Только в эти выходные:\n"
                        "• Скидка 20% на все номера\n"
                        "• Бесплатный поздний выезд\n"
                        "• Комплимент от шеф-повара\n\n"
                        "Промокод: WEEKEND20"
            },
            "family": {
                "title": "👨‍👩‍👧‍👦 Семейные каникулы!",
                "text": "Специальное предложение для семей:\n"
                        "• Дети до 12 лет - бесплатно\n"
                        "• Семейный номер со скидкой 30%\n"
                        "• Бесплатные развлечения для детей\n\n"
                        "Действует весь месяц!"
            },
            "birthday": {
                "title": "🎂 День рождения в подарок!",
                "text": "Отмечайте день рождения у нас:\n"
                        "• Скидка 50% имениннику\n"
                        "• Торт в подарок\n"
                        "• Украшение номера\n"
                        "• Поздравление от команды\n\n"
                        "Забронируйте за неделю!"
            }
        }

        offer = offers.get(offer_type)
        if not offer:
            return

        success_count = 0
        for user in users:
            try:
                await self.bot.send_message(
                    user.telegram_id,
                    f"{offer['title']}\n\n{offer['text']}\n\n"
                    f"Забронировать: /book",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="📅 Забронировать со скидкой",
                            callback_data=f"promo_book_{offer_type}"
                        )],
                        [InlineKeyboardButton(
                            text="❌ Отписаться от рассылки",
                            callback_data="unsubscribe_offers"
                        )]
                    ])
                )
                success_count += 1
                await asyncio.sleep(0.1)  # Защита от флуда
            except Exception as e:
                logger.error(f"Error sending offer to user {user.telegram_id}: {e}")

        # Отчет админу
        await self.bot.send_message(
            ADMIN_TELEGRAM_ID,
            f"📊 Рассылка '{offer['title']}' завершена\n"
            f"Отправлено: {success_count}/{len(users)}"
        )

    async def daily_statistics(self, session: AsyncSession):
        """Ежедневная статистика для администратора"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # Статистика за вчера
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.created_at >= yesterday,
                    Booking.created_at < today
                )
            )
        )
        yesterday_bookings = result.scalars().all()

        # Текущие гости
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.check_in <= today,
                    Booking.check_out > today,
                    Booking.status == "confirmed"
                )
            )
        )
        current_guests = result.scalars().all()

        # Заезды сегодня
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.check_in == today,
                    Booking.status.in_(["confirmed", "pending"])
                )
            )
        )
        today_checkins = result.scalars().all()

        # Выезды сегодня
        result = await session.execute(
            select(Booking).where(
                and_(
                    Booking.check_out == today,
                    Booking.status == "confirmed"
                )
            )
        )
        today_checkouts = result.scalars().all()

        # Расчет выручки
        yesterday_revenue = sum(b.total_price for b in yesterday_bookings if b.status != "cancelled")

        # Отправка отчета
        await self.bot.send_message(
            ADMIN_TELEGRAM_ID,
            f"📊 Ежедневный отчет за {yesterday.strftime('%d.%m.%Y')}\n\n"
            f"💰 Выручка: {yesterday_revenue:,.0f} сум\n"
            f"📝 Новых бронирований: {len(yesterday_bookings)}\n"
            f"🏠 Текущих гостей: {len(current_guests)}\n\n"
            f"Сегодня {today.strftime('%d.%m.%Y')}:\n"
            f"➡️ Заезды: {len(today_checkins)}\n"
            f"⬅️ Выезды: {len(today_checkouts)}\n\n"
            f"Детальный отчет: /admin_report"
        )