import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from gui.main_window import MainWindow
from gui.download_page import DownloadPage
from gui.styles import DARK_THEME, DIALOG_STYLE
from core.config import VK_CLIENT_ID, VK_GROUP_ID, VK_API_VERSION
import argparse
import os

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('youtube_vk_downloader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        # Создаем необходимые директории
        os.makedirs('data', exist_ok=True)
        os.makedirs('downloads', exist_ok=True)
        
        # Парсим аргументы командной строки
        parser = argparse.ArgumentParser()
        parser.add_argument('--test', action='store_true', help='Запуск в тестовом режиме')
        args = parser.parse_args()
        
        # Инициализируем Qt
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        app = QApplication(sys.argv)
        
        # Инициализируем WebEngine
        profile = QWebEngineProfile.defaultProfile()
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Применяем темную тему и стили для диалогов
        app.setStyleSheet(DARK_THEME + DIALOG_STYLE)
        
        # Создаем главное окно
        window = MainWindow()
        
        # Добавляем статус бар
        window.status_bar = window.statusBar()
        
        # Добавляем страницы
        download_page = DownloadPage()
        window.content_area.addWidget(download_page)
        
        # Показываем окно
        window.show()
        
        # Если включен тестовый режим
        if args.test:
            logger.info("Тестовый режим активирован")
            # Добавляем тестовые данные
            from core.main import get_video_info
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            info = get_video_info(test_url)
            if info:
                window.download_page.url_input.setText(test_url)
        
        # Запускаем приложение
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 