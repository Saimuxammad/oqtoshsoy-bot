import sqlite3
import os

# Путь к базе данных
db_path = "oqtoshsoy.db"  # Укажите правильный путь, если нужно

# Новые изображения для каждого номера (ID: новый URL)
new_images = {
    1: "https://imgur.com/a/kClmlHr",  # Стандарт 2-х местный
    2: "https://i.imgur.com/ваш_новый_url.jpg",  # Люкс 2-х местный
    3: "https://i.imgur.com/ваш_новый_url.jpg",  # Стандарт 4-х местный
    # Добавьте остальные номера по необходимости
}


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

        # Обновляем URL изображений для каждого номера
        for room_id, image_url in new_images.items():
            cursor.execute(
                "UPDATE rooms SET image_url = ? WHERE id = ?",
                (image_url, room_id)
            )
            print(f"Обновлено изображение для номера ID {room_id}")

        # Сохраняем изменения и закрываем соединение
        conn.commit()
        conn.close()

        print("Все изображения успешно обновлены")
        return True

    except Exception as e:
        print(f"Ошибка при обновлении изображений: {str(e)}")
        return False


if __name__ == "__main__":
    update_room_images()