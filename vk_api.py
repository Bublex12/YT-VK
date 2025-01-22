import requests
import json
import logging
from urllib.parse import urlencode
from config import VK_ACCESS_TOKEN, VK_API_VERSION

logger = logging.getLogger(__name__)

class VkApi:
    def __init__(self):
        self.access_token = VK_ACCESS_TOKEN
        self.api_version = VK_API_VERSION
        self.base_url = "https://id.vk.com/oauth2"
        
    def get_auth_url(self, redirect_uri, state):
        """Получение URL для авторизации"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'scope': 'email phone',
            'redirect_uri': redirect_uri,
            'state': state,
            'code_challenge_method': 'S256',
            'v': self.api_version
        }
        return f"{self.base_url}/authorize?{urlencode(params)}"
        
    def get_access_token(self, code, redirect_uri, device_id):
        """Получение access token по коду авторизации"""
        try:
            params = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'code': code,
                'redirect_uri': redirect_uri,
                'device_id': device_id
            }
            
            response = requests.post(f"{self.base_url}/auth", data=params)
            response.raise_for_status()
            
            data = response.json()
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'expires_in': data.get('expires_in'),
                'user_id': data.get('user_id')
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении access token: {str(e)}")
            raise
            
    def refresh_token(self, refresh_token, device_id):
        """Обновление access token"""
        try:
            params = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'refresh_token': refresh_token,
                'device_id': device_id
            }
            
            response = requests.post(f"{self.base_url}/auth", data=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении токена: {str(e)}")
            raise
            
    def get_user_info(self, access_token):
        """Получение информации о пользователе"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f"{self.base_url}/user_info", headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о пользователе: {str(e)}")
            raise
            
    def logout(self, access_token):
        """Выход из аккаунта"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.post(f"{self.base_url}/logout", headers=headers)
            response.raise_for_status()
            
            return response.json().get('response') == 1
            
        except Exception as e:
            logger.error(f"Ошибка при выходе: {str(e)}")
            raise 