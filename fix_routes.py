import os
import requests
import json

# URL вашего приложения
BASE_URL = "https://web-production-1c8d.up.railway.app"

# Проверка статуса сервера
def check_status():
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Статус сервера: {response.status_code}")
        print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
    except Exception as e:
        print(f"Ошибка при проверке статуса: {e}")

# Вызов эндпоинта проверки webapp
def check_webapp():
    try:
        response = requests.get(f"{BASE_URL}/check-webapp")
        print(f"Статус check-webapp: {response.status_code}")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Ошибка при проверке webapp: {e}")

# Обновление настроек в конфигурации
def update_settings():
    try:
        # Данный эндпоинт нужно добавить в ваше приложение
        response = requests.post(f"{BASE_URL}/fix-webapp-route", json={
            "update_routes": True
        })
        print(f"Статус обновления настроек: {response.status_code}")
        print(response.text)
    except Exception as e:
        print(f"Ошибка при обновлении настроек: {e}")

if __name__ == "__main__":
    print("Диагностика веб-приложения")
    print("-" * 50)
    print("1. Проверка статуса сервера")
    check_status()
    print("\n2. Проверка эндпоинта webapp")
    check_webapp()
    print("\n3. Обновление настроек (требует создания эндпоинта)")
    # update_settings() # Раскомментируйте после добавления эндпоинта