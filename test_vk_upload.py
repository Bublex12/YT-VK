from vk_api import VkApi
from config import VK_GROUP_ID
import logging
import os
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    try:
        vk_api = VkApi()
        
        # Получаем токен автоматически
        access_token = vk_api.get_current_token()
        if not access_token:
            logger.error("Не удалось получить токен. Запустите test_vk_auth.py для авторизации")
            return
            
        # Проверяем токен
        if not vk_api.check_token(access_token):
            logger.error("Недействительный токен. Запустите test_vk_auth.py для обновления токена")
            return
            
        # Путь к тестовому видео
        video_path = "downloads\Building an iOS Calculator using Python - PyVisual_1737557840_5633\Building an iOS Calculator using Python - PyVisual.mp4"  # Укажите путь к вашему видео
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Файл не найден: {video_path}")
            
        # Загружаем видео
        result = vk_api.upload_video(
            access_token=access_token,
            video_path=video_path,
            title="Тестовое видео",
            description="Загружено через API",
            is_private=1,  # 1 - только для друзей, 0 - для всех
            group_id=VK_GROUP_ID  # None для загрузки на страницу пользователя
        )
        
        # Получаем ID видео
        owner_id = result.get('owner_id')
        video_id = result.get('video_id')
        
        if owner_id and video_id:
            # Проверяем статус загрузки
            for _ in range(10):  # Проверяем 10 раз
                status = vk_api.get_video_status(access_token, owner_id, video_id)
                processing = status.get('processing')
                
                if not processing:
                    logger.info("Видео успешно обработано")
                    logger.info(f"Ссылка на видео: {status.get('player')}")
                    break
                    
                logger.info("Видео в процессе обработки...")
                time.sleep(5)  # Ждем 5 секунд перед следующей проверкой
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    main() 