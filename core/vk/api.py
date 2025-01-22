import logging
from .session import VkSession, VkApiError
from .events import EventEmitter, UploadEvent
from dataclasses import dataclass
from typing import Optional, List
import time

logger = logging.getLogger(__name__)

@dataclass
class UploadTask:
    path: str
    title: str
    source_url: str = ""
    group_id: Optional[int] = None
    description: str = ""
    is_private: bool = False
    status: str = "pending"
    progress: float = 0
    error: Optional[str] = None
    retry_count: int = 0
    created_at: float = time.time()
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def get_full_description(self) -> str:
        """Формирование полного описания с ссылкой на оригинал"""
        desc = self.description or ""
        if self.source_url:
            if desc:
                desc += "\n\n"
            desc += f"ОРИГИНАЛ - {self.source_url}"
        return desc

class VkApi(EventEmitter):
    def __init__(self, client_id, api_version):
        super().__init__()
        self.session = VkSession(client_id, api_version)
        self.upload_queue: List[UploadTask] = []
        self._active_uploads = 0
        self.MAX_CONCURRENT_UPLOADS = 2
        self.MAX_RETRIES = 3
        
    def get_user_groups(self, user_id=None):
        """Получение групп пользователя с кэшированием"""
        try:
            params = {
                'filter': 'admin,editor,moder',
                'extended': 1,
                'fields': 'can_upload_video'
            }
            if user_id:
                params['user_id'] = user_id
                
            return self.session.request('groups.get', params)
            
        except Exception as e:
            logger.error(f"Failed to get user groups: {e}")
            raise
            
    def upload_video(self, video_path: str, title: str, **kwargs) -> UploadTask:
        """Добавление видео в очередь загрузки"""
        task = UploadTask(
            path=video_path,
            title=title,
            **kwargs
        )
        
        self.upload_queue.append(task)
        self.emit(UploadEvent.QUEUED, task)
        
        # Запускаем обработку очереди
        self._process_upload_queue()
        return task
        
    def cancel_upload(self, task: UploadTask):
        """Отмена загрузки"""
        if task in self.upload_queue:
            task.status = "cancelled"
            self.emit(UploadEvent.CANCELLED, task)
            self.upload_queue.remove(task)
            
    def retry_upload(self, task: UploadTask):
        """Повторная попытка загрузки"""
        if task.retry_count < self.MAX_RETRIES:
            task.status = "pending"
            task.retry_count += 1
            task.error = None
            self.emit(UploadEvent.RETRY, task)
            self._process_upload_queue()
            
    def _process_upload_queue(self):
        """Обработка очереди загрузок"""
        if self._active_uploads >= self.MAX_CONCURRENT_UPLOADS:
            return
            
        for task in self.upload_queue:
            if task['status'] == 'pending':
                self._start_upload(task)
                break
                
    def _start_upload(self, task: UploadTask):
        """Начало загрузки видео"""
        self._active_uploads += 1
        task.status = "uploading"
        task.started_at = time.time()
        
        self.emit(UploadEvent.STARTED, task)
        
        try:
            # Получаем URL для загрузки
            upload_url = self._get_upload_url(task)
            
            def progress_callback(progress: float):
                task.progress = progress
                self.emit(UploadEvent.PROGRESS, task)
            
            # Загружаем видео
            result = self._upload_to_server(
                upload_url, 
                task.path,
                progress_callback
            )
            
            task.status = "completed"
            task.completed_at = time.time()
            self.emit(UploadEvent.COMPLETED, task, result)
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.emit(UploadEvent.FAILED, task)
            logger.error(f"Upload failed: {e}")
            
            # Автоматический ретрай
            if task.retry_count < self.MAX_RETRIES:
                self.retry_upload(task)
                
        finally:
            self._active_uploads -= 1
            self._process_upload_queue() 

    def get_queue_status(self):
        """Получение статуса очереди"""
        return {
            'active': self._active_uploads,
            'pending': len([t for t in self.upload_queue if t.status == 'pending']),
            'completed': len([t for t in self.upload_queue if t.status == 'completed']),
            'failed': len([t for t in self.upload_queue if t.status == 'failed'])
        }
        
    def clear_completed(self):
        """Очистка завершенных загрузок"""
        self.upload_queue = [
            task for task in self.upload_queue 
            if task.status not in ('completed', 'cancelled')
        ]
        
    def pause_queue(self):
        """Приостановка очереди"""
        self.MAX_CONCURRENT_UPLOADS = 0
        
    def resume_queue(self):
        """Возобновление очереди"""
        self.MAX_CONCURRENT_UPLOADS = 2
        self._process_upload_queue() 