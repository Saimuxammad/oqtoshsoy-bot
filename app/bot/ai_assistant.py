# app/bot/ai_assistant.py

from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta


class OqtoshsoyAssistant:
    """Умный ассистент для помощи пользователям"""

    def __init__(self):
        self.faq = {
            "парковка": "🚗 У нас есть бесплатная охраняемая парковка на 50 мест",
            "питание": "🍽 Завтрак включен в стоимость. Обед и ужин - по меню ресторана",
            "трансфер": "🚌 Организуем трансфер из Ташкента за 500,000 сум в обе стороны",
            "дети": "👶 Дети до 5 лет - бесплатно. Есть детская площадка и аниматоры",
            "бассейн": "🏊 Открытый бассейн работает с мая по октябрь, крытый - круглый год",
            "wi-fi": "📶 Бесплатный Wi-Fi на всей территории курорта",
            "животные": "🐕 К сожалению, размещение с животными не предусмотрено",
            "оплата": "💳 Принимаем наличные, карты Uzcard/Humo, переводы",
            "отмена": "❌ Бесплатная отмена за 48 часов до заезда",
            "документы": "📄 Нужен только паспорт или ID-карта"
        }

        self.recommendations = {
            "романтика": ["Люкс 2-х местный", "VIP номера"],
            "семья": ["Стандарт 4-х местный", "Апартамент", "Коттедж"],
            "компания": ["Коттедж 6-местный", "Президентский апартамент", "Тапчаны"],
            "эконом": ["Стандарт 2-х местный", "Тапчаны"],
            "премиум": ["Президентский апартамент", "VIP номера"]
        }

    def process_question(self, text: str) -> Dict[str, any]:
        """Обрабатывает вопрос пользователя"""
        text_lower = text.lower()

        # Поиск в FAQ
        for key, answer in self.faq.items():
            if key in text_lower:
                return {
                    "type": "faq",
                    "answer": answer,
                    "suggestions": self._get_related_questions(key)
                }

        # Рекомендации номеров
        for category, rooms in self.recommendations.items():
            if category in text_lower:
                return {
                    "type": "recommendation",
                    "rooms": rooms,
                    "reason": f"Рекомендуем для {category}"
                }

        # Вопросы о датах
        if any(word in text_lower for word in ["когда", "свободно", "даты", "забронировать"]):
            return {
                "type": "availability",
                "action": "check_dates"
            }

        # Вопросы о ценах
        if any(word in text_lower for word in ["цена", "стоимость", "сколько"]):
            return {
                "type": "pricing",
                "action": "show_prices"
            }

        return {
            "type": "unknown",
            "suggestions": [
                "🏨 Посмотреть номера",
                "📅 Проверить доступность",
                "💰 Узнать цены",
                "❓ Частые вопросы"
            ]
        }

    def _get_related_questions(self, topic: str) -> List[str]:
        """Возвращает связанные вопросы"""
        related = {
            "парковка": ["Как добраться?", "Есть ли трансфер?"],
            "питание": ["Что включено в завтрак?", "Работает ли ресторан?"],
            "дети": ["Есть ли детское меню?", "Работает ли аниматор?"]
        }
        return related.get(topic, [])

    def get_personalized_greeting(self, user_name: str, time_of_day: str) -> str:
        """Персонализированное приветствие"""
        greetings = {
            "morning": f"🌅 Доброе утро, {user_name}! Планируете отдых в горах?",
            "afternoon": f"☀️ Добрый день, {user_name}! Самое время забронировать отдых!",
            "evening": f"🌙 Добрый вечер, {user_name}! Мечтаете о горном воздухе?",
            "night": f"🌃 Доброй ночи, {user_name}! Планируете отдых заранее?"
        }
        return greetings.get(time_of_day, f"👋 Здравствуйте, {user_name}!")


# Обработчик для умного ассистента
@router.message(F.text.startswith("?") | F.text.startswith("Вопрос:"))
async def ai_assistant_handler(message: Message, session: AsyncSession):
    assistant = OqtoshsoyAssistant()

    # Убираем префикс
    question = message.text.lstrip("?").lstrip("Вопрос:").strip()

    # Обрабатываем вопрос
    result = assistant.process_question(question)

    if result["type"] == "faq":
        # Отвечаем на FAQ
        keyboard = []
        for suggestion in result.get("suggestions", []):
            keyboard.append([InlineKeyboardButton(
                text=suggestion,
                callback_data=f"ask_{suggestion[:20]}"
            )])
        keyboard.append([InlineKeyboardButton(
            text="💬 Связаться с менеджером",
            callback_data="contact_manager"
        )])

        await message.answer(
            f"{result['answer']}\n\n"
            f"Есть еще вопросы?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    elif result["type"] == "recommendation":
        # Показываем рекомендованные номера
        rooms = await get_all_rooms(session)
        recommended = [r for r in rooms if r.name in result["rooms"]]

        text = f"🎯 {result['reason']}:\n\n"
        keyboard = []

        for room in recommended[:3]:  # Показываем топ-3
            text += f"• {room.name} - от {room.price_per_night:,} сум\n"
            keyboard.append([InlineKeyboardButton(
                text=f"👁 {room.name}",
                callback_data=f"room_{room.id}"
            )])

        keyboard.append([InlineKeyboardButton(
            text="📋 Все номера",
            callback_data="all_rooms"
        )])

        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    elif result["type"] == "availability":
        # Предлагаем выбрать даты
        await message.answer(
            "📅 Давайте проверим доступность номеров.\n"
            "На какие даты вы планируете отдых?",
            reply_markup=generate_calendar_keyboard(
                datetime.now().year,
                datetime.now().month
            )
        )

    elif result["type"] == "pricing":
        # Показываем диапазон цен
        await message.answer(
            "💰 Стоимость номеров в Oqtoshsoy:\n\n"
            "🏠 Эконом (Стандарт): 700,000 - 1,200,000 сум\n"
            "🏡 Комфорт (VIP): 1,300,000 - 1,900,000 сум\n"
            "🏰 Премиум (Апартаменты): 1,800,000 - 4,500,000 сум\n"
            "🎪 Тапчаны: 300,000 - 500,000 сум\n\n"
            "💡 В выходные цены выше на 20-30%",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Подробный прайс", callback_data="detailed_prices")],
                [InlineKeyboardButton(text="🔍 Подобрать по бюджету", callback_data="budget_search")]
            ])
        )

    else:
        # Не поняли вопрос
        keyboard = []
        for suggestion in result.get("suggestions", []):
            keyboard.append([InlineKeyboardButton(
                text=suggestion,
                callback_data=f"menu_{suggestion[:20]}"
            )])

        await message.answer(
            "🤔 Не совсем понял ваш вопрос. Могу помочь с:\n\n"
            "• Выбором номера\n"
            "• Бронированием\n"
            "• Информацией о курорте\n"
            "• Ценами и условиями\n\n"
            "Выберите тему или напишите вопрос по-другому:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )