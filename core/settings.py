import json
import os
import logging

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self, settings_file='data/settings.json'):
        self.settings_file = settings_file
        self.settings = {
            'default_group_id': None,
            'default_group_name': None,
            'download_path': 'downloads',
            'theme': 'dark',
            'auto_upload': False,
            'save_thumbnails': True
        }
        self.load_settings()
        
    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек: {str(e)}")
            
    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {str(e)}")
            
    def get(self, key, default=None):
        """Получение значения настройки"""
        return self.settings.get(key, default)
        
    def set(self, key, value):
        """Установка значения настройки"""
        self.settings[key] = value
        self.save_settings() 