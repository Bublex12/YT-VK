from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QProgressBar, QListWidget, QLabel,
    QListWidgetItem, QMessageBox, QDialog, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from .widgets.video_item import VideoListItem
from core.vk_api import VkApi
from core.main import download_youtube_video, get_video_info
import logging
import os
import json
from core.database import VideoDatabase

logger = logging.getLogger(__name__)

class DownloadThread(QThread):
    progress = pyqtSignal(str, float)
    finished = pyqtSignal(bool, str, str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            # Получаем информацию о видео
            logger.info(f"Начинаем получение информации о видео: {self.url}")
            info = get_video_info(self.url)
            if not info:
                raise ValueError("Не удалось получить информацию о видео")
                
            self.title = info.get('title', 'Без названия')
            logger.info(f"Получена информация о видео: {self.title}")
            
            # Скачиваем видео
            video_path, thumb_path = download_youtube_video(self.url)
            if not video_path or not os.path.exists(video_path):
                raise ValueError(f"Видео не было скачано или файл не найден: {video_path}")
                
            logger.info(f"Видео успешно скачано: {video_path}")
            self.finished.emit(True, video_path, self.title)
            
        except Exception as e:
            logger.error("Критическая ошибка в потоке загрузки:", exc_info=True)
            self.finished.emit(False, str(e), '')

class UploadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, vk_api, access_token, video_path, title, description=None, thumbnail_path=None):
        super().__init__()
        self.vk_api = vk_api
        self.access_token = access_token
        self.video_path = video_path
        self.title = title
        self.description = description
        self.thumbnail_path = thumbnail_path
        
    def run(self):
        try:
            logger.info(f"Начинаем загрузку видео в VK: {self.title}")
            
            result = self.vk_api.upload_video(
                access_token=self.access_token,
                video_path=self.video_path,
                title=self.title,
                description=self.description,
                is_private=0,
                group_id=self.vk_api.group_id,
                thumbnail_path=self.thumbnail_path
            )
            
            owner_id = result.get('owner_id')
            video_id = result.get('video_id')
            
            if owner_id and video_id:
                video_url = f"https://vk.com/video{owner_id}_{video_id}"
                logger.info(f"Видео успешно загружено: {video_url}")
                self.progress.emit("Видео успешно загружено")
                self.finished.emit(True, video_url)
            else:
                logger.error("Не получены owner_id или video_id")
                self.finished.emit(False, "Ошибка при получении ID видео")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке видео в VK: {str(e)}")
            self.finished.emit(False, str(e))

class DownloadPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vk_api = VkApi()
        self.downloaded_videos = {}
        
        # Инициализируем БД с правильным путем
        db_path = os.path.join('data', 'videos.db')
        self.db = VideoDatabase(db_path)
        
        self.load_downloaded_videos()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # URL инпут и кнопка загрузки
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Введите URL видео с YouTube')
        url_layout.addWidget(self.url_input)
        
        self.download_button = QPushButton('Скачать видео')
        self.download_button.clicked.connect(self.start_download)
        url_layout.addWidget(self.download_button)
        
        layout.addLayout(url_layout)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Список видео
        list_label = QLabel("Скачанные видео:")
        list_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(list_label)
        
        self.videos_list = QListWidget()
        layout.addWidget(self.videos_list)
        
        # Загружаем сохраненные видео в список
        self.refresh_videos_list()

    def load_downloaded_videos(self):
        try:
            if os.path.exists('downloads/videos.json'):
                with open('downloads/videos.json', 'r', encoding='utf-8') as f:
                    self.downloaded_videos = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке истории скачиваний: {str(e)}")
            self.downloaded_videos = {}
            
    def save_downloaded_videos(self):
        try:
            os.makedirs('downloads', exist_ok=True)
            with open('downloads/videos.json', 'w', encoding='utf-8') as f:
                json.dump(self.downloaded_videos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении истории скачиваний: {str(e)}")
            
    def refresh_videos_list(self):
        self.videos_list.clear()
        for video_id, video_info in self.downloaded_videos.items():
            if os.path.exists(video_info['path']):
                item = QListWidgetItem(self.videos_list)
                widget = VideoListItem(video_info['title'], video_info['path'], parent=self)
                
                # Подключаем обработчик для кнопки удаления
                widget.delete_button.clicked.connect(
                    lambda checked, path=video_info['path']: 
                    self.delete_video(path)
                )
                
                item.setSizeHint(widget.sizeHint())
                self.videos_list.setItemWidget(item, widget)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, 'Ошибка', 'Введите URL видео')
            return
            
        logger.info(f"Начинаем обработку URL: {url}")
        
        # Проверяем токен VK
        access_token = self.vk_api.get_current_token()
        if not access_token:
            logger.error("Токен VK не найден")
            QMessageBox.warning(
                self, 
                'Ошибка', 
                'Не найден токен VK. Запустите test_vk_auth.py для авторизации'
            )
            return
            
        if not self.vk_api.check_token(access_token):
            logger.error("Токен VK недействителен")
            QMessageBox.warning(
                self, 
                'Ошибка', 
                'Токен VK недействителен. Запустите test_vk_auth.py для обновления'
            )
            return
            
        logger.info("Токен VK проверен успешно")
        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Создаем и запускаем поток для загрузки
        try:
            self.download_thread = DownloadThread(url)
            self.download_thread.progress.connect(self.update_progress)
            self.download_thread.finished.connect(self.handle_download_complete)
            self.download_thread.start()
            logger.info("Поток загрузки запущен")
        except Exception as e:
            logger.error(f"Ошибка при создании потока загрузки: {str(e)}")
            self.download_button.setEnabled(True)
            QMessageBox.warning(self, 'Ошибка', f'Не удалось начать загрузку: {str(e)}')

    def update_progress(self, message, percent):
        if percent >= 0:
            self.progress_bar.setValue(int(percent))
        logger.info(message)

    def handle_download_complete(self, success, video_path, title):
        if success:
            video_id = os.path.basename(os.path.dirname(video_path))
            self.downloaded_videos[video_id] = {
                'title': title,
                'path': video_path,
                'uploaded_to_vk': False
            }
            self.save_downloaded_videos()
            self.refresh_videos_list()
            
        self.download_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        if not success:
            QMessageBox.warning(self, 'Ошибка', f'Ошибка при скачивании: {video_path}')

    def handle_upload_complete(self, success, result, widget=None):
        if widget:
            if success:
                widget.status_label.setText("Загружено в VK")
                widget.status_label.setStyleSheet("color: green")
                widget.upload_button.setEnabled(False)
                QMessageBox.information(
                    self, 
                    'Успех', 
                    f'Видео успешно загружено в VK\nСсылка: {result}'
                )
            else:
                widget.status_label.setText("Ошибка загрузки")
                widget.status_label.setStyleSheet("color: red")
                widget.upload_button.setEnabled(True)
                QMessageBox.warning(
                    self, 
                    'Ошибка', 
                    f'Ошибка при загрузке в VK: {result}'
                )

    def show_error(self, message):
        """Показ сообщения об ошибке"""
        QMessageBox.warning(self, 'Ошибка', message)

    def upload_to_vk(self, video_path, title):
        """Загрузка видео в ВК"""
        try:
            # Проверяем существование файлов
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Видео файл не найден: {video_path}")
            
            # Находим виджет для обновления статуса
            widget = None
            for i in range(self.videos_list.count()):
                item = self.videos_list.item(i)
                widget = self.videos_list.itemWidget(item)
                if widget.video_path == video_path:
                    widget.status_label.setText("Загрузка: 0%")
                    widget.upload_button.setText("Отмена")
                    widget.is_uploading = True
                    break
            
            # Функция для обновления прогресса
            def update_progress(progress):
                if widget:
                    widget.status_label.setText(f"Загрузка: {progress}%")
                
            # Функция для проверки отмены
            def check_cancel():
                return widget and not widget.is_uploading
            
            # Загружаем видео
            response = self.vk_api.upload_video(
                video_path=video_path,
                title=title,
                description=None,
                thumb_path=None,
                progress_callback=update_progress,
                cancel_check=check_cancel
            )
            
            logger.info(f"Видео успешно загружено в ВК: {response}")
            
            # Обновляем статус виджета
            if widget:
                widget.status_label.setText("Загружено")
                widget.status_label.setStyleSheet("color: green")
                widget.upload_button.setText("Загрузить в VK")
                widget.upload_button.setEnabled(False)
                widget.is_uploading = False
                
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке видео в VK: {str(e)}")
            self.show_error(f"Ошибка при загрузке: {str(e)}")
            
            # Возвращаем виджет в исходное состояние
            if widget:
                widget.status_label.setText("Ошибка")
                widget.status_label.setStyleSheet("color: red")
                widget.upload_button.setText("Загрузить в VK")
                widget.upload_button.setEnabled(True)
                widget.is_uploading = False
                
            return False

    def delete_video(self, video_path):
        try:
            # Находим ID видео по пути
            video_id = None
            for vid_id, info in self.downloaded_videos.items():
                if info['path'] == video_path:
                    video_id = vid_id
                    break
            
            if video_id:
                # Удаляем файлы
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        logger.info(f"Файл удален: {video_path}")
                    
                    # Удаляем директорию, если она пуста
                    video_dir = os.path.dirname(video_path)
                    if os.path.exists(video_dir) and not os.listdir(video_dir):
                        os.rmdir(video_dir)
                        logger.info(f"Директория удалена: {video_dir}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении файлов: {str(e)}")
                
                # Удаляем из словаря и сохраняем изменения
                del self.downloaded_videos[video_id]
                self.save_downloaded_videos()
                logger.info(f"Видео удалено из списка: {video_id}")
                
                # Обновляем список
                self.refresh_videos_list()
                
        except Exception as e:
            logger.error(f"Ошибка при удалении видео: {str(e)}")
            QMessageBox.warning(self, 'Ошибка', f'Не удалось удалить видео: {str(e)}')

    def schedule_upload(self, video_path):
        """Планирование загрузки видео"""
        from .scheduled_page import ScheduleDialog
        
        dialog = ScheduleDialog(video_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            upload_time = dialog.datetime_edit.dateTime().toString()
            # Получаем доступ к странице запланированных загрузок через главное окно
            main_window = self.window()
            if hasattr(main_window, 'scheduled_page'):
                main_window.scheduled_page.add_scheduled_upload(video_path, upload_time)
                QMessageBox.information(
                    self,
                    "Успех",
                    "Загрузка успешно запланирована"
                ) 

    def add_stats_widget(self):
        """Добавление виджета статистики"""
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: #2b2b2b;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                color: white;
            }
        """)
        
        layout = QHBoxLayout(stats_frame)
        
        stats = [
            ("📥 Скачано", len(self.downloaded_videos)),
            ("📤 Загружено", self.db.get_uploaded_count()),
            ("⏰ Запланировано", self.parent().scheduled_page.get_scheduled_count())
        ]
        
        for title, value in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            
            value_label = QLabel(str(value))
            value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
            title_label = QLabel(title)
            
            stat_layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignCenter)
            stat_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
            
            layout.addWidget(stat_widget)
        
        self.layout().insertWidget(1, stats_frame) 