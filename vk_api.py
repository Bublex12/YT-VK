import requests
import json
import logging
import webbrowser
from urllib.parse import urlencode
from config import VK_CLIENT_ID, VK_GROUP_ID, VK_API_VERSION
import os
from token_manager import TokenManager
import time

logger = logging.getLogger(__name__)

class VkApi:
    def __init__(self):
        self.client_id = VK_CLIENT_ID
        self.group_id = VK_GROUP_ID
        self.api_version = VK_API_VERSION
        self.base_url = "https://oauth.vk.com"
        self.api_base_url = "https://api.vk.com/method"
        self.token_manager = TokenManager()
        
    def get_auth_url(self):
        """Получение URL для авторизации через Implicit Flow"""
        params = {
            'client_id': self.client_id,
            'display': 'page',
            'redirect_uri': 'https://oauth.vk.com/blank.html',
            'scope': 'video,offline,groups',
            'response_type': 'token',
            'v': self.api_version
        }
        return f"{self.base_url}/authorize?{urlencode(params)}"
    
    def check_token(self, access_token):
        """Проверка валидности токена"""
        try:
            params = {
                'access_token': access_token,
                'v': self.api_version
            }
            response = requests.get(f"{self.api_base_url}/users.get", params=params)
            response.raise_for_status()
            return response.json().get('response') is not None
        except:
            return False
            
    def get_user_info(self, access_token):
        """Получение информации о пользователе"""
        try:
            params = {
                'access_token': access_token,
                'v': self.api_version
            }
            response = requests.get(f"{self.api_base_url}/users.get", params=params)
            response.raise_for_status()
            return response.json().get('response', [{}])[0]
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе: {str(e)}")
            raise
    
    def get_upload_server(self, access_token, group_id=None):
        """Получение сервера для загрузки видео"""
        try:
            params = {
                'access_token': access_token,
                'v': self.api_version
            }
            if group_id:
                params['group_id'] = group_id
                
            response = requests.get(f"{self.api_base_url}/video.save", params=params)
            response.raise_for_status()
            return response.json().get('response', {})
        except Exception as e:
            logger.error(f"Ошибка при получении сервера для загрузки: {str(e)}")
            raise 

    def upload_video(self, access_token, video_path, title=None, description=None, is_private=0, group_id=None):
        """Загрузка видео в ВК"""
        try:
            video_path = os.path.normpath(video_path)
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Файл не найден: {video_path}")
            
            logger.info(f"Загружаем файл: {video_path}")
            logger.info(f"Название для загрузки: {title}")
            
            # Получаем сервер для загрузки
            save_data = self.get_upload_server(access_token, group_id)
            upload_url = save_data.get('upload_url')
            
            if not upload_url:
                raise ValueError("Не удалось получить URL для загрузки")
            
            # Загружаем файл
            logger.info("Шаг 1: Загрузка файла на сервер...")
            with open(video_path, 'rb') as video_file:
                files = {'video_file': (os.path.basename(video_path), video_file, 'video/mp4')}
                response = requests.post(upload_url, files=files)
                response.raise_for_status()
                logger.debug(f"Ответ сервера на загрузку файла: {response.text}")
            
                upload_result = response.json()
                video_hash = upload_result.get('video_hash')
                if not video_hash:
                    raise ValueError("Не получен video_hash после загрузки")
            
            # Сохраняем видео с названием
            logger.info("Шаг 2: Сохранение видео с параметрами...")
            params = {
                'access_token': access_token,
                'v': self.api_version,
                'video_hash': video_hash,
                'is_private': is_private,
                'group_id': group_id if group_id else None,
                'name': title,
                'description': description
            }
            
            # Удаляем None значения
            params = {k: v for k, v in params.items() if v is not None}
            
            logger.info(f"Отправляем запрос к video.save с параметрами: {params}")
            response = requests.get(f"{self.api_base_url}/video.save", params=params)
            response.raise_for_status()
            
            result = response.json().get('response', {})
            logger.info(f"Ответ на сохранение видео: {result}")
            
            if not result.get('title') and title:
                logger.warning(f"Название видео не установлено. Ответ API: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке видео: {str(e)}")
            raise

    def get_video_status(self, access_token, owner_id, video_id):
        """Получение статуса загрузки видео"""
        try:
            params = {
                'access_token': access_token,
                'v': self.api_version,
                'videos': f"{owner_id}_{video_id}"
            }
            
            response = requests.get(f"{self.api_base_url}/video.get", params=params)
            response.raise_for_status()
            
            return response.json().get('response', {}).get('items', [{}])[0]
            
        except Exception as e:
            logger.error(f"Ошибка при получении статуса видео: {str(e)}")
            raise 

    def get_current_token(self):
        """Получение текущего токена"""
        return self.token_manager.get_token() 