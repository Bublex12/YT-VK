from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from gui.dialogs.auth_dialog import VKAuthDialog
from core.vk_api import VkApi
import sys
import logging
import argparse
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('vk_auth.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        # Инициализируем Qt
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        app = QApplication(sys.argv)
        
        # Настраиваем WebEngine
        profile = QWebEngineProfile.defaultProfile()
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        
        # Добавляем парсинг аргументов
        parser = argparse.ArgumentParser()
        parser.add_argument('--force-refresh', action='store_true', help='Принудительное обновление токена')
        parser.add_argument('--check', action='store_true', help='Проверка текущего токена')
        args = parser.parse_args()
        
        # Инициализируем VK API
        vk_api = VkApi()
        
        if args.check:
            # Просто проверяем токен
            if vk_api.ensure_token():
                user_info = vk_api.get_user_info(vk_api.get_current_token())
                logger.info(f"Токен действителен. Авторизован как: {user_info.get('first_name')} {user_info.get('last_name')}")
                expires_in = vk_api.token_manager.token_data.get('expires_in', 0)
                if expires_in > 0:
                    created_at = datetime.fromisoformat(vk_api.token_manager.token_data.get('created_at'))
                    expires_at = created_at + timedelta(seconds=expires_in)
                    logger.info(f"Токен действителен до: {expires_at}")
            else:
                logger.warning("Токен недействителен или отсутствует")
            return
            
        if args.force_refresh:
            # Принудительное обновление
            if vk_api.refresh_token(force=True):
                logger.info("Токен успешно обновлен")
            else:
                logger.error("Не удалось обновить токен")
            return
            
        # Проверяем существующий токен
        if vk_api.ensure_token():
            logger.info("Найден действующий токен")
            user_info = vk_api.get_user_info(vk_api.get_current_token())
            logger.info(f"Авторизован как: {user_info.get('first_name')} {user_info.get('last_name')}")
            return
            
        # Если токен не найден или недействителен, показываем диалог авторизации
        auth_url = vk_api.get_auth_url()
        dialog = VKAuthDialog(auth_url)
        
        # Обрабатываем результат авторизации
        if dialog.exec() == VKAuthDialog.DialogCode.Accepted:
            logger.info("Авторизация успешна")
            
            # Получаем информацию о пользователе
            user_info = vk_api.get_user_info(vk_api.get_current_token())
            logger.info(f"Авторизован как: {user_info.get('first_name')} {user_info.get('last_name')}")
        else:
            logger.warning("Авторизация отменена пользователем")
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 