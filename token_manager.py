import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TokenManager:
    def __init__(self, token_file='config/token.json'):
        self.token_file = token_file
        self.token_data = self._load_token()
    
    def _load_token(self):
        """Загрузка токена из файла"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке токена: {str(e)}")
        return {}
    
    def _save_token(self):
        """Сохранение токена в файл"""
        try:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as f:
                json.dump(self.token_data, f, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении токена: {str(e)}")
    
    def save_token_from_url(self, url):
        """Сохранение токена из URL после авторизации"""
        try:
            # Извлекаем параметры из URL
            fragment = url.split('#')[1]
            params = dict(param.split('=') for param in fragment.split('&'))
            
            self.token_data = {
                'access_token': params.get('access_token'),
                'user_id': params.get('user_id'),
                'expires_in': int(params.get('expires_in', 0)),
                'created_at': datetime.now().isoformat()
            }
            self._save_token()
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении токена из URL: {str(e)}")
            return False
    
    def get_token(self):
        """Получение текущего токена"""
        if not self.token_data:
            return None
            
        # Проверяем срок действия токена
        created_at = datetime.fromisoformat(self.token_data.get('created_at', '2000-01-01'))
        expires_in = self.token_data.get('expires_in', 0)
        
        if expires_in > 0:  # Если токен временный
            expires_at = created_at + timedelta(seconds=expires_in)
            if datetime.now() > expires_at:
                logger.warning("Токен истек")
                return None
                
        return self.token_data.get('access_token') 