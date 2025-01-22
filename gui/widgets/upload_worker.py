from PyQt6.QtCore import QObject, pyqtSignal
import logging
import json

logger = logging.getLogger(__name__)

class UploadWorker(QObject):
    progress = pyqtSignal(float)
    finished = pyqtSignal(bool, dict)
    
    def __init__(self, vk_api, video_path, title, group_id=None, source_url=""):
        super().__init__()
        self.vk_api = vk_api
        self.video_path = video_path
        self.title = title
        self.group_id = group_id
        self.source_url = source_url
        
    def run(self):
        try:
            # Формируем описание с ссылкой на оригинал
            description = ""
            if self.source_url:
                description = f"ОРИГИНАЛ - {self.source_url}"
            
            # Функция для обновления прогресса
            def progress_callback(value):
                self.progress.emit(value)
            
            # Загружаем видео
            result = self.vk_api.upload_video(
                video_path=self.video_path,
                title=self.title,
                description=description,
                group_id=self.group_id,
                progress_callback=progress_callback
            )
            
            # Проверяем наличие необходимых полей
            if result and 'owner_id' in result and 'video_id' in result:
                self.finished.emit(True, result)
            else:
                raise ValueError("Не удалось получить информацию о загруженном видео")
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            self.finished.emit(False, {'error': str(e)}) 