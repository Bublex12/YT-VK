import sys
import uuid
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from vk_api import VkApi
from token_manager import TokenManager
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запроса от VK после авторизации"""
        try:
            # Парсим параметры из URL
            query_components = parse_qs(urlparse(self.path).query)
            
            # Проверяем наличие кода авторизации
            if 'code' in query_components:
                code = query_components['code'][0]
                state = query_components['state'][0] if 'state' in query_components else None
                
                # Проверяем state
                if state != self.server.vk_api.state:
                    raise ValueError("Invalid state parameter")
                
                # Генерируем device_id
                device_id = str(uuid.uuid4())
                
                # Получаем токен
                token_data = self.server.vk_api.get_access_token(code, device_id)
                logger.info("Получен токен доступа")
                
                # Получаем информацию о пользователе
                user_info = self.server.vk_api.get_user_info(token_data['access_token'])
                logger.info(f"Информация о пользователе: {user_info}")
                
                # Отправляем успешный ответ
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write("Авторизация успешна! Можете закрыть это окно.".encode())
                
                # Сохраняем токен для дальнейшего использования
                self.server.auth_result = {
                    'token_data': token_data,
                    'user_info': user_info
                }
                
            else:
                raise ValueError("No authorization code provided")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке callback: {str(e)}")
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"Ошибка авторизации: {str(e)}".encode())
        
        finally:
            # Останавливаем сервер после обработки запроса
            self.server.running = False

def main():
    try:
        token_manager = TokenManager()
        vk_api = VkApi()
        
        # Проверяем существующий токен
        current_token = token_manager.get_token()
        if current_token and vk_api.check_token(current_token):
            logger.info("Используем существующий токен")
            return current_token
        
        # Получаем новый токен
        auth_url = vk_api.get_auth_url()
        logger.info(f"URL авторизации: {auth_url}")
        
        # Открываем браузер для авторизации
        webbrowser.open(auth_url)
        
        print("\nПосле авторизации скопируйте полный URL из адресной строки (включая access_token)")
        url = input("Вставьте URL: ").strip()
        
        if token_manager.save_token_from_url(url):
            logger.info("Токен успешно сохранен")
            return token_manager.get_token()
        else:
            logger.error("Не удалось сохранить токен")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        return None

if __name__ == "__main__":
    token = main()
    if token:
        print(f"\nТокен успешно получен и сохранен")
    else:
        print("\nНе удалось получить токен") 