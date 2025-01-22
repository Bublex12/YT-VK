import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QLineEdit, QPushButton, QProgressBar, 
    QTextEdit, QMessageBox, QHBoxLayout, QCheckBox,
    QListWidget, QListWidgetItem, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMetaObject, Q_ARG
from PyQt6.QtGui import QIcon
from main import download_youtube_video, get_video_info, logger
from vk_api import VkApi
import logging
import os
import json
import traceback
import time
from time import sleep

class VideoListItem(QWidget):
    def __init__(self, title, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        layout = QHBoxLayout(self)
        
        # Название видео
        self.title_label = QLabel(title)
        layout.addWidget(self.title_label, stretch=1)
        
        # Кнопка загрузки в VK
        self.upload_button = QPushButton("Загрузить в VK")
        self.upload_button.setFixedWidth(120)
        layout.addWidget(self.upload_button)
        
        # Статус загрузки
        self.status_label = QLabel("")
        self.status_label.setFixedWidth(150)
        layout.addWidget(self.status_label)
        
        # Кнопка удаления
        self.delete_button = QPushButton("Удалить")
        self.delete_button.setFixedWidth(80)
        self.delete_button.setStyleSheet("QPushButton { background-color: #ff4444; color: white; }")
        layout.addWidget(self.delete_button)
        
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

class UploadWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, vk_api, access_token, video_path, title, description=None):
        super().__init__()
        self.vk_api = vk_api
        self.access_token = access_token
        self.video_path = video_path
        self.title = title
        self.description = description
        
    def run(self):
        try:
            logger.info(f"Начинаем загрузку видео в VK: {self.title}")
            
            # Загружаем видео с оригинальным названием
            result = self.vk_api.upload_video(
                access_token=self.access_token,
                video_path=self.video_path,
                title=self.title,
                description=self.description,
                is_private=0,
                group_id=self.vk_api.group_id
            )
            
            # Если получили ответ без ошибок, значит видео успешно загружено
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

class YouTubeVkDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.vk_api = VkApi()
        self.downloaded_videos = {}  # Словарь для хранения информации о скачанных видео
        self.load_downloaded_videos()  # Загружаем историю скачиваний
        self.init_ui()
        self.setup_logging()
        
    def init_ui(self):
        self.setWindowTitle('YouTube to VK Downloader')
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
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
        
        # Список скачанных видео
        list_label = QLabel("Скачанные видео:")
        layout.addWidget(list_label)
        
        self.videos_list = QListWidget()
        layout.addWidget(self.videos_list)
        
        # Загружаем сохраненные видео в список
        self.refresh_videos_list()
        
        # Лог
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
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
                widget = VideoListItem(video_info['title'], video_info['path'])
                
                # Подключаем обработчик для кнопки загрузки
                widget.upload_button.clicked.connect(
                    lambda checked, path=video_info['path'], title=video_info['title']: 
                    self.upload_to_vk(path, title)
                )
                
                # Подключаем обработчик для кнопки удаления
                widget.delete_button.clicked.connect(
                    lambda checked, path=video_info['path']: 
                    self.delete_video(path)
                )
                
                item.setSizeHint(widget.sizeHint())
                self.videos_list.addItem(item)
                self.videos_list.setItemWidget(item, widget)
                
    def handle_download_complete(self, success, video_path, title):
        if success:
            # Сохраняем информацию о видео с оригинальным названием
            video_id = os.path.basename(os.path.dirname(video_path))
            self.downloaded_videos[video_id] = {
                'title': title,  # Сохраняем оригинальное название
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
                QMessageBox.warning(
                    self, 
                    'Ошибка', 
                    f'Ошибка при загрузке в VK: {result}'
                )
            
    def upload_to_vk(self, video_path, title):
        try:
            logger.info(f"Инициализация загрузки видео в VK: {title}")
            # Находим виджет для обновления статуса
            for i in range(self.videos_list.count()):
                item = self.videos_list.item(i)
                widget = self.videos_list.itemWidget(item)
                if widget.video_path == video_path:
                    widget.status_label.setText("Загрузка...")
                    widget.upload_button.setEnabled(False)
                    
                    access_token = self.vk_api.get_current_token()
                    if not access_token:
                        raise ValueError("Требуется авторизация VK")
                    
                    # Создаем и запускаем поток для загрузки
                    self.upload_thread = UploadWorker(
                        self.vk_api,
                        access_token,
                        video_path,
                        title,
                        description=None
                    )
                    self.upload_thread.progress.connect(logger.info)
                    self.upload_thread.finished.connect(
                        lambda success, result: self.handle_upload_complete(success, result, widget)
                    )
                    self.upload_thread.start()
                    break
                    
        except Exception as e:
            logger.error(f"Ошибка при инициализации загрузки в VK: {str(e)}")
            QMessageBox.warning(self, 'Ошибка', str(e))

    def setup_logging(self):
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Создаем форматтер для логов
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Хендлер для файла
        try:
            file_handler = logging.FileHandler('youtube_vk_downloader.log', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Ошибка при создании файлового хендлера: {e}")
        
        # Хендлер для GUI
        class QTextEditLogger(logging.Handler):
            def __init__(self, widget):
                super().__init__()
                self.widget = widget
                self.widget.setReadOnly(True)
                
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # Используем invokeMethod для обновления GUI из другого потока
                    QMetaObject.invokeMethod(self.widget, "append",
                                           Qt.ConnectionType.QueuedConnection,
                                           Q_ARG(str, msg))
                except Exception as e:
                    print(f"Ошибка при логировании в GUI: {e}")
        
        gui_handler = QTextEditLogger(self.log_text)
        gui_handler.setFormatter(formatter)
        gui_handler.setLevel(logging.INFO)
        root_logger.addHandler(gui_handler)

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
            logger.error(f"Полный стек ошибки:\n{traceback.format_exc()}")
            self.download_button.setEnabled(True)
            QMessageBox.warning(self, 'Ошибка', f'Не удалось начать загрузку: {str(e)}')
        
    def update_progress(self, message, percent):
        if percent >= 0:
            self.progress_bar.setValue(int(percent))
        logger.info(message)

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
            try:
                info = get_video_info(self.url)
                if not info:
                    raise ValueError("Не удалось получить информацию о видео")
                    
                self.title = info.get('title', 'Без названия')  # Сохраняем оригинальное название
                logger.info(f"Получена информация о видео: {self.title}")
                
            except Exception as e:
                logger.error("Ошибка при получении информации о видео:", exc_info=True)
                raise
            
            # Скачиваем видео с оригинальным названием
            logger.info(f"Начинаем скачивание видео: {self.title}")
            try:
                video_path, thumb_path = download_youtube_video(self.url, title=self.title)  # Передаем название
                if not video_path or not os.path.exists(video_path):
                    raise ValueError(f"Видео не было скачано или файл не найден: {video_path}")
                    
                logger.info(f"Видео успешно скачано: {video_path}")
                
            except Exception as e:
                logger.error("Ошибка при скачивании видео:", exc_info=True)
                raise
            
            self.finished.emit(True, video_path, self.title)  # Передаем оригинальное название
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Критическая ошибка в потоке загрузки:", exc_info=True)
            self.finished.emit(False, error_msg, '')

def main():
    try:
        # Настраиваем отлов всех исключений
        def exception_hook(exctype, value, traceback):
            logger.error(f"Необработанное исключение:", exc_info=(exctype, value, traceback))
            sys.__excepthook__(exctype, value, traceback)  # Вызываем стандартный обработчик
        
        sys.excepthook = exception_hook
        
        app = QApplication(sys.argv)
        window = YouTubeVkDownloader()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.error(f"Критическая ошибка в main:", exc_info=True)
        raise

if __name__ == '__main__':
    main() 