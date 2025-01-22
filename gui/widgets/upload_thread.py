from PyQt6.QtCore import QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class UploadThread(QThread):
    progress = pyqtSignal(float)  # Сигнал прогресса (0-100)
    finished = pyqtSignal(bool, dict)  # Сигнал завершения (успех/неуспех, результат)
    
    def __init__(self, vk_api, video_path, title, parent=None, group_id=None, source_url=""):
        super().__init__(parent)
        self.vk_api = vk_api
        self.video_path = video_path
        self.title = title
        self.group_id = group_id
        self.source_url = source_url
        self.is_cancelled = False
        
    def run(self):
        try:
            # Формируем описание с ссылкой на оригинал
            description = ""
            if self.source_url:
                description = f"ОРИГИНАЛ - {self.source_url}"
            
            # Функция обновления прогресса
            def progress_callback(value):
                self.progress.emit(value)
                
            # Функция проверки отмены
            def cancel_check():
                return self.is_cancelled
            
            # Загружаем видео
            result = self.vk_api.upload_video(
                video_path=self.video_path,
                title=self.title,
                description=description,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
                group_id=self.group_id  # Передаем ID группы
            )
            
            self.finished.emit(True, result)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке видео: {str(e)}")
            self.finished.emit(False, {'error': str(e)})
    
    def cancel(self):
        """Отмена загрузки"""
        self.is_cancelled = True 