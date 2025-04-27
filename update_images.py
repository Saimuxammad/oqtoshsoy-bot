import sqlite3
import os
import json

# Путь к базе данных
db_path = "oqtoshsoy.db"  # Укажите правильный путь, если нужно

# Список фотографий для стандартного номера (ID 1)
standard_room_photos = [
    "https://imgur.com/njJXDo1",
    "https://imgur.com/LRgKg5y",
    "https://imgur.com/Boeke4g",
    "https://imgur.com/SAS86LR",
    "https://imgur.com/zSmB3i4",
    "https://imgur.com/8I61dlC"
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

        # Сохраняем изменения и закрываем соединение
        conn.commit()
        conn.close()

        print("Изображения успешно обновлены")
        return True

    except Exception as e:
        print(f"Ошибка при обновлении изображений: {str(e)}")
        return False


if __name__ == "__main__":
    update_room_images()