import requests
import json
import logging
import webbrowser
from urllib.parse import urlencode
from .config import VK_CLIENT_ID, VK_GROUP_ID, VK_API_VERSION
import os
from .token_manager import TokenManager
import time
from datetime import datetime, timedelta
from .upload_tracker import UploadTracker
from .vk.events import EventEmitter, UploadEvent
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class VkApi(EventEmitter):
    def __init__(self):
        super().__init__()  # Важно вызвать конструктор родителя
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
                'v': self.api_version,
                'fields': 'photo_50'  # Запрашиваем фото
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

    def upload_video(self, video_path, title, description=None, group_id=None, progress_callback=None):
        """Загрузка видео в ВК"""
        try:
            # Получаем URL для загрузки
            save_data = self._get_upload_url(title, description, group_id)
            upload_url = save_data.get('upload_url')
            
            if not upload_url:
                raise ValueError("URL для загрузки не найден")
            
            # Загружаем файл
            file_size = os.path.getsize(video_path)
            with open(video_path, 'rb') as video_file:
                files = {'video_file': video_file}
                
                response = requests.post(
                    upload_url,
                    files=files,
                    stream=True
                )
                
                if response.ok:
                    if progress_callback:
                        progress_callback(100)
                    
                    # Возвращаем данные из video.save
                    return {
                        'owner_id': save_data.get('owner_id'),
                        'video_id': save_data.get('video_id'),
                        'access_key': save_data.get('access_key'),
                        'title': save_data.get('title'),
                        'description': save_data.get('description')
                    }
                else:
                    raise Exception(f"Upload failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
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

    def get_videos(self, access_token, owner_id=None):
        """Получение списка видео из группы"""
        try:
            # Используем ID группы со знаком минус, так как это группа
            group_id = -int(self.group_id)  # Добавляем минус для групп
            
            params = {
                'access_token': access_token,
                'v': self.api_version,
                'owner_id': group_id,  # ID группы со знаком минус
                'extended': 1,  # Расширенная информация
                'count': 200    # Максимальное количество
            }
            
            response = requests.get(f"{self.api_base_url}/video.get", params=params)
            response.raise_for_status()
            
            result = response.json().get('response', {})
            items = result.get('items', [])
            
            # Преобразуем даты и форматируем данные
            videos = []
            for item in items:
                videos.append({
                    'id': item.get('id'),
                    'owner_id': item.get('owner_id'),
                    'title': item.get('title', 'Без названия'),
                    'description': item.get('description', ''),
                    'views': item.get('views', 0),
                    'likes': item.get('likes', {}).get('count', 0),
                    'date': time.strftime('%d.%m.%Y', time.localtime(item.get('date', 0))),
                    'duration': item.get('duration', 0),
                    'thumb_url': item.get('photo_800') or item.get('photo_320') or item.get('photo_130'),
                    'player_url': item.get('player'),
                    'platform': item.get('platform', ''),
                    'privacy_view': item.get('privacy_view', {}).get('category', 'all'),
                    'comments': item.get('comments', 0),
                    'reposts': item.get('reposts', {}).get('count', 0)
                })
                
            return videos
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка видео группы: {str(e)}")
            raise

    def delete_video(self, access_token, owner_id, video_id):
        """Удаление видео"""
        try:
            params = {
                'access_token': access_token,
                'v': self.api_version,
                'owner_id': owner_id,
                'video_id': video_id
            }
            
            response = requests.get(f"{self.api_base_url}/video.delete", params=params)
            response.raise_for_status()
            
            return response.json().get('response') == 1
            
        except Exception as e:
            logger.error(f"Ошибка при удалении видео: {str(e)}")
            raise 

    def get_video_upload_url(self, access_token, video_id=None, owner_id=None):
        """Получение URL для загрузки превью"""
        try:
            params = {
                'access_token': access_token,
                'v': self.api_version
            }
            
            if video_id:
                params['video_id'] = video_id
            if owner_id:
                params['owner_id'] = owner_id
            
            logger.debug(f"Запрос URL для загрузки превью: {params}")
            response = requests.get(f"{self.api_base_url}/video.save", params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Ответ сервера video.save: {data}")
            
            if 'error' in data:
                error = data['error']
                logger.error(f"Ошибка VK API: {error['error_code']} - {error['error_msg']}")
                raise ValueError(f"Ошибка VK API: {error['error_msg']}")
            
            result = data.get('response', {})
            upload_url = result.get('upload_url')
            
            if not upload_url:
                logger.error("URL для загрузки не найден в ответе")
                raise ValueError("URL для загрузки не найден в ответе")
            
            logger.info(f"Получен URL для загрузки: {upload_url}")
            return upload_url
            
        except Exception as e:
            logger.error(f"Ошибка при получении URL для загрузки: {str(e)}")
            raise

    def edit_video(self, access_token, owner_id, video_id, **params):
        """Редактирование видео"""
        try:
            # Формируем параметры для обновления информации
            api_params = {
                'access_token': access_token,
                'v': self.api_version,
                'owner_id': owner_id,
                'video_id': video_id
            }
            
            # Маппинг параметров
            if 'title' in params:
                api_params['name'] = params['title']
            if 'description' in params:
                api_params['description'] = params['description']
            if 'privacy_view' in params:
                privacy_map = {'all': 0, 'friends': 1, 'private': 2}
                api_params['privacy_view'] = privacy_map.get(params['privacy_view'], 0)
            if 'comments_enabled' in params:
                api_params['no_comments'] = int(not params['comments_enabled'])
            if 'no_search' in params:
                api_params['no_search'] = int(params['no_search'])
            if 'age_restriction' in params:
                if params['age_restriction'] > 0:
                    api_params['age_restriction'] = params['age_restriction']
            if 'publish_date' in params:
                api_params['publish_date'] = params['publish_date']
            
            # Предупреждение если пытаются изменить превью
            if 'thumbnail_path' in params:
                logger.warning("VK API не поддерживает изменение превью для существующих видео")
            
            logger.debug(f"Параметры обновления видео: {api_params}")
            
            # Обновляем информацию о видео
            response = requests.get(f"{self.api_base_url}/video.edit", params=api_params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Ответ сервера video.edit: {data}")
            
            if 'error' in data:
                error = data['error']
                logger.error(f"Ошибка VK API: {error['error_code']} - {error['error_msg']}")
                raise ValueError(f"Ошибка VK API: {error['error_msg']}")
            
            if data.get('response') != 1:
                logger.error("Неожиданный ответ при обновлении видео")
                raise ValueError("Не удалось обновить информацию о видео")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при редактировании видео: {str(e)}")
            raise

    def get_video_stats(self, access_token, video_id, owner_id=None):
        """Получение статистики видео"""
        try:
            if owner_id is None:
                owner_id = -int(self.group_id)
            
            params = {
                'access_token': access_token,
                'v': self.api_version,
                'owner_id': owner_id,
                'video_id': video_id
            }
            
            response = requests.get(f"{self.api_base_url}/video.getStats", params=params)
            response.raise_for_status()
            
            return response.json().get('response', {})
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики видео: {str(e)}")
            raise 

    def handle_auth_data(self, auth_data):
        """Обработка данных авторизации"""
        try:
            access_token = auth_data.get('access_token')
            if not access_token:
                raise ValueError("Токен не получен")
            
            # Проверяем токен
            if not self.check_token(access_token):
                raise ValueError("Полученный токен недействителен")
            
            # Сохраняем все данные авторизации
            self.token_manager.token_data = {
                'access_token': access_token,
                'user_id': auth_data.get('user_id'),
                'expires_in': int(auth_data.get('expires_in', 0)),
                'created_at': datetime.now().isoformat()
            }
            self.token_manager._save_token()
            logger.info("Данные авторизации успешно сохранены")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке данных авторизации: {str(e)}")
            return False

    def refresh_token(self, force=False):
        """Принудительное обновление токена"""
        try:
            current_token = self.get_current_token()
            
            # Проверяем необходимость обновления
            if not force and current_token and self.check_token(current_token):
                logger.debug("Токен действителен, обновление не требуется")
                return True
            
            logger.info("Начинаем обновление токена")
            
            # Показываем диалог авторизации
            from gui.dialogs.auth_dialog import VKAuthDialog
            auth_url = self.get_auth_url()
            dialog = VKAuthDialog(auth_url)
            
            if dialog.exec() == VKAuthDialog.DialogCode.Accepted:
                logger.info("Токен успешно обновлен")
                return True
            else:
                logger.warning("Обновление токена отменено пользователем")
                return False
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении токена: {str(e)}")
            return False

    def ensure_token(self):
        """Проверка и обновление токена при необходимости"""
        token = self.get_current_token()
        
        if not token:
            logger.info("Токен не найден")
            return self.refresh_token()
        
        # Проверяем срок действия
        created_at = datetime.fromisoformat(self.token_manager.token_data.get('created_at', '2000-01-01'))
        expires_in = self.token_manager.token_data.get('expires_in', 0)
        
        if expires_in > 0:  # Если токен временный
            expires_at = created_at + timedelta(seconds=expires_in)
            time_left = expires_at - datetime.now()
            
            # Обновляем токен за день до истечения
            if time_left.days < 1:
                logger.info("Срок действия токена истекает, начинаем обновление")
                return self.refresh_token()
        
        # Проверяем валидность токена
        if not self.check_token(token):
            logger.info("Токен недействителен")
            self.token_manager.clear_token()
            return self.refresh_token()
        
        return True 

    def _get_upload_url(self, title, description='', group_id=None):
        """Получение URL для загрузки видео"""
        try:
            params = {
                'access_token': self.get_current_token(),
                'v': self.api_version,
                'name': title,
                'description': description,
                'wallpost': 0,
                'is_private': 0,
                'repeat': 0
            }
            
            if group_id:
                params['group_id'] = group_id
            
            logger.debug(f"Запрос URL для загрузки видео: {params}")
            response = requests.get(f"{self.api_base_url}/video.save", params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Ответ сервера video.save: {data}")
            
            if 'error' in data:
                error = data['error']
                raise ValueError(f"Ошибка VK API: {error['error_msg']}")
            
            if 'response' not in data:
                raise ValueError("Неверный формат ответа от сервера")
            
            return data['response']
            
        except Exception as e:
            logger.error(f"Ошибка при получении URL для загрузки: {str(e)}")
            raise 

    def get_user_groups(self):
        """Получение списка групп пользователя с правами на загрузку видео"""
        try:
            params = {
                'access_token': self.get_current_token(),
                'v': self.api_version,
                'filter': 'admin,editor,moder',
                'extended': 1,
                'fields': 'can_upload_video'
            }
            
            response = requests.get(f"{self.api_base_url}/groups.get", params=params)
            response.raise_for_status()
            
            data = response.json()
            if 'error' in data:
                raise ValueError(f"Ошибка VK API: {data['error']['error_msg']}")
            
            groups = []
            for item in data.get('response', {}).get('items', []):
                if item.get('can_upload_video', 0) == 1:
                    groups.append({
                        'id': item['id'],
                        'name': item['name'],
                        'photo': item.get('photo_50')
                    })
            
            return groups
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка групп: {str(e)}")
            raise 