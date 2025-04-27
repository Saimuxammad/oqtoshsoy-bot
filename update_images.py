import sqlite3
import os
import json

# Путь к базе данных
db_path = "oqtoshsoy.db"  # Укажите правильный путь, если нужно

# Список фотографий для стандартного номера (ID 1)
standard_room_photos = [
    "[img]https://i.imgur.com/Boeke4g.jpeg[/img]",
    "[img]https://i.imgur.com/njJXDo1.jpeg[/img]",
    "[img]https://i.imgur.com/SAS86LR.jpeg[/img]",
    "[img]https://i.imgur.com/LRgKg5y.jpeg[/img]",
    "[img]https://i.imgur.com/SAS86LR.jpeg[/img]",
    "[img]https://i.imgur.com/zSmB3i4.jpeg[/img]",
    "[img]https://i.imgur.com/8I61dlC.jpeg[/img]"
]

# Важно: Преобразуйте ссылки в прямые ссылки на изображения, добавив '.jpg' и заменив imgur.com на i.imgur.com
standard_room_photos_direct = [url.replace("https://imgur.com/", "https://i.imgur.com/") + ".jpg" for url in
                               standard_room_photos]


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
            (standard_room_photos_direct[0], json.dumps(standard_room_photos_direct), 1)
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


# Важно: запустить функцию обновления при выполнении скрипта
if __name__ == "__main__":
    update_room_images()