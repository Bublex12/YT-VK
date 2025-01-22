from enum import Enum
from typing import Callable, Dict, List
import logging

logger = logging.getLogger(__name__)

class UploadEvent(Enum):
    STARTED = "upload_started"
    PROGRESS = "upload_progress"
    COMPLETED = "upload_completed"
    FAILED = "upload_failed"
    QUEUED = "upload_queued"
    CANCELLED = "upload_cancelled"
    RETRY = "upload_retry"

class EventEmitter:
    def __init__(self):
        self._listeners: Dict[UploadEvent, List[Callable]] = {
            event: [] for event in UploadEvent
        }
        
    def on(self, event: UploadEvent, callback: Callable):
        """Подписка на событие"""
        self._listeners[event].append(callback)
        
    def emit(self, event: UploadEvent, *args, **kwargs):
        """Вызов обработчиков события"""
        for callback in self._listeners[event]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler: {e}") 