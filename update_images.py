import sqlite3
import os
import json

# Путь к базе данных
db_path = "oqtoshsoy.db"  # Укажите правильный путь, если нужно

# Список фотографий для стандартного номера (ID 1)
# Правильный формат: прямые ссылки на изображения
standard_room_photos = [
    "https://i.imgur.com/Boeke4g.jpg",
    "https://i.imgur.com/njJXDo1.jpg",
    "https://i.imgur.com/sAS86LR.jpg",
    "https://i.imgur.com/LRgKg5y.jpg",
    "https://i.imgur.com/sAS86LR.jpg",
    "https://i.imgur.com/zSmB314.jpg",
    "https://i.imgur.com/8I61dlC.jpg"
]


def update_room_images():
    """Обновляет изображения номеров в базе данных"""
    try:
        # Проверяем существование файла БД
        if not os.path.exists(db_path):
            print(f"Ошибка: файл базы данных {db_path} не найден")
            return False

        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Обновляем основное изображение и массив photos для номера "Стандарт 2-х местный"
        cursor.execute(
            "UPDATE rooms SET image_url = ?, photos = ? WHERE id = ?",
            (standard_room_photos[0], json.dumps(standard_room_photos), 1)
        )

        print(f"Обновлено изображение и галерея для номера ID 1")

        # Проверяем, что данные успешно обновлены
        cursor.execute("SELECT image_url, photos FROM rooms WHERE id = 1")
        result = cursor.fetchone()
        if result:
            print(f"В базе данных теперь: image_url = {result[0]}")
            print(f"В базе данных теперь: photos = {result[1]}")

        # Сохраняем изменения и закрываем соединение
        conn.commit()
        conn.close()

        print("Изображения успешно обновлены!")
        return True

    except Exception as e:
        print(f"Ошибка при обновлении изображений: {str(e)}")
        return False


# Вызываем функцию при запуске скрипта
if __name__ == "__main__":
    print("Запуск обновления изображений...")
    update_room_images()
    print("Обновление завершено.")