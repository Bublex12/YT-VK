import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Общие настройки
OUTPUT_DIR = "downloads"  # Директория для сохранения видео

# Конфигурация ВКонтакте
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")
if not VK_ACCESS_TOKEN:
    raise ValueError("Не указан VK_ACCESS_TOKEN в .env файле")

VK_API_VERSION = os.getenv("VK_API_VERSION", "5.131")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")  # Опционально

# Общие настройки
MAX_VIDEO_SIZE_MB = 2048  # Максимальный размер видео в МБ
REQUEST_TIMEOUT = 30  # Таймаут для HTTP-запросов в секундах

# Добавьте эти параметры в config.py
VK_CLIENT_ID = "ваш_client_id"  # ID вашего приложения VK
VK_REDIRECT_URI = "http://localhost:8000/callback"  # URI для редиректа после авторизации 