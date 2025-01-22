from datetime import datetime, timedelta
import logging
import requests
from ..token_manager import TokenManager

logger = logging.getLogger(__name__)

class VkSession:
    def __init__(self, client_id, api_version):
        self.client_id = client_id
        self.api_version = api_version
        self.token_manager = TokenManager()
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_delay = 0.34  # ~3 запроса в секунду
        
    def request(self, method, params=None, max_retries=3):
        """Выполнение запроса с ретраями и контролем частоты"""
        params = params or {}
        params.update({
            'access_token': self.token_manager.get_token(),
            'v': self.api_version
        })
        
        for attempt in range(max_retries):
            try:
                # Контроль частоты запросов
                self._wait_request_limit()
                
                response = self.session.get(
                    f"https://api.vk.com/method/{method}",
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                if 'error' in data:
                    error = data['error']
                    if error['error_code'] == 5:  # Invalid token
                        self._handle_token_error()
                        continue
                    raise VkApiError(error)
                    
                return data.get('response')
                
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                    
    def _wait_request_limit(self):
        """Ожидание между запросами"""
        now = datetime.now().timestamp()
        wait_time = self.last_request_time + self.request_delay - now
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_request_time = now
        
    def _handle_token_error(self):
        """Обработка ошибки токена"""
        self.token_manager.clear_token()
        if not self.ensure_token():
            raise VkApiError("Failed to refresh token")

class VkApiError(Exception):
    pass 