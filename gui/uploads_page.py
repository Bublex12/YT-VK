from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QDialog, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QDesktopServices
from PyQt6.QtCore import QUrl
from core.vk_api import VkApi
import logging
import requests
import json
import os

logger = logging.getLogger(__name__)

class VkVideoItem(QWidget):
    def __init__(self, video_data, parent=None):
        super().__init__(parent)
        self.video_data = video_data
        self.init_ui()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Превью видео
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(120, 68)
        self.thumbnail.setStyleSheet("border: 1px solid #666;")
        self.load_thumbnail()
        layout.addWidget(self.thumbnail)
        
        # Информация о видео
        info_layout = QVBoxLayout()
        
        # Название и длительность
        title_layout = QHBoxLayout()
        title = QLabel(self.video_data.get('title', 'Без названия'))
        title.setStyleSheet("font-weight: bold; color: white;")
        title_layout.addWidget(title)
        
        duration = self.format_duration(self.video_data.get('duration', 0))
        duration_label = QLabel(duration)
        duration_label.setStyleSheet("color: #888;")
        title_layout.addWidget(duration_label)
        title_layout.addStretch()
        
        info_layout.addLayout(title_layout)
        
        # Статистика
        stats_layout = QHBoxLayout()
        
        # Просмотры
        views = QLabel(f"👁 {self.format_number(self.video_data.get('views', 0))}")
        views.setStyleSheet("color: #888;")
        views.setToolTip("Количество просмотров")
        stats_layout.addWidget(views)
        
        # Лайки
        likes = QLabel(f"👍 {self.format_number(self.video_data.get('likes', 0))}")
        likes.setStyleSheet("color: #888;")
        likes.setToolTip("Количество лайков")
        stats_layout.addWidget(likes)
        
        # Комментарии
        comments = QLabel(f"💬 {self.format_number(self.video_data.get('comments', 0))}")
        comments.setStyleSheet("color: #888;")
        comments.setToolTip("Количество комментариев")
        stats_layout.addWidget(comments)
        
        # Репосты
        reposts = QLabel(f"↪ {self.format_number(self.video_data.get('reposts', 0))}")
        reposts.setStyleSheet("color: #888;")
        reposts.setToolTip("Количество репостов")
        stats_layout.addWidget(reposts)
        
        # Дата и приватность
        date = QLabel(self.video_data.get('date', ''))
        date.setStyleSheet("color: #888;")
        stats_layout.addWidget(date)
        
        privacy = self.get_privacy_icon(self.video_data.get('privacy_view', 'all'))
        privacy_label = QLabel(privacy)
        privacy_label.setStyleSheet("color: #888;")
        privacy_label.setToolTip(
            {
                'all': 'Доступно всем',
                'friends': 'Только друзьям',
                'private': 'Только мне'
            }.get(
                self.video_data.get('privacy_view', 'all'),
                'Доступно всем'
            )
        )
        stats_layout.addWidget(privacy_label)
        
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Кнопки управления
        buttons_layout = QVBoxLayout()
        
        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.setFixedWidth(100)
        self.edit_btn.setToolTip("Редактировать информацию о видео")
        buttons_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setFixedWidth(100)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.delete_btn.setToolTip("Удалить видео")
        buttons_layout.addWidget(self.delete_btn)
        
        layout.addLayout(buttons_layout)
        
        # Подсказка для превью
        if self.video_data.get('description'):
            self.thumbnail.setToolTip(self.video_data['description'])
        
    def load_thumbnail(self):
        try:
            thumbnail_url = self.video_data.get('thumb_url')
            if thumbnail_url:
                response = requests.get(thumbnail_url)
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaled(
                    120, 68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.thumbnail.setPixmap(pixmap)
            else:
                self.thumbnail.setText("Нет превью")
                self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception as e:
            logger.error(f"Ошибка при загрузке превью: {str(e)}")
            self.thumbnail.setText("Ошибка")

    @staticmethod
    def format_number(num):
        """Форматирование чисел (1000 -> 1K)"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)
        
    @staticmethod
    def format_duration(seconds):
        """Форматирование длительности"""
        minutes = seconds // 60
        hours = minutes // 60
        if hours > 0:
            return f"{hours}:{minutes%60:02d}:{seconds%60:02d}"
        return f"{minutes}:{seconds%60:02d}"
        
    @staticmethod
    def get_privacy_icon(privacy):
        """Получение иконки приватности"""
        icons = {
            'all': '🌍',      # Доступно всем
            'friends': '👥',   # Только друзьям
            'private': '🔒'    # Только мне
        }
        return icons.get(privacy, '🌍')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.pos())
            
    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Открыть в браузере
        if self.video_data.get('player_url'):
            open_action = menu.addAction("Открыть в браузере")
            open_action.triggered.connect(self.open_in_browser)
        
        # Копировать ссылку
        copy_link_action = menu.addAction("Копировать ссылку")
        copy_link_action.triggered.connect(self.copy_link)
        
        # Копировать название
        copy_title_action = menu.addAction("Копировать название")
        copy_title_action.triggered.connect(self.copy_title)
        
        menu.addSeparator()
        
        # Редактировать
        edit_action = menu.addAction("Редактировать")
        edit_action.triggered.connect(lambda: self.edit_btn.click())
        
        # Удалить
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(lambda: self.delete_btn.click())
        delete_action.setIcon(QIcon.fromTheme("edit-delete"))
        
        menu.exec(self.mapToGlobal(pos))
        
    def open_in_browser(self):
        """Открытие видео в браузере"""
        url = self.video_data.get('player_url')
        if url:
            QDesktopServices.openUrl(QUrl(url))
            
    def copy_link(self):
        """Копирование ссылки на видео"""
        owner_id = self.video_data.get('owner_id')
        video_id = self.video_data.get('id')
        if owner_id and video_id:
            link = f"https://vk.com/video{owner_id}_{video_id}"
            QApplication.clipboard().setText(link)
            
    def copy_title(self):
        """Копирование названия видео"""
        title = self.video_data.get('title', '')
        if title:
            QApplication.clipboard().setText(title)

class LoadVideosThread(QThread):
    videos_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, vk_api):
        super().__init__()
        self.vk_api = vk_api
        
    def run(self):
        try:
            access_token = self.vk_api.get_current_token()
            if not access_token:
                raise ValueError("Требуется авторизация VK")
                
            # Получаем список видео из VK
            videos = self.vk_api.get_videos(access_token)
            self.videos_loaded.emit(videos)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке видео: {str(e)}")
            self.error_occurred.emit(str(e))

class UploadsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vk_api = VkApi()
        self.init_ui()
        self.load_videos()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок и кнопки
        header_layout = QHBoxLayout()
        
        title = QLabel("Загруженные видео")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_videos)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Список видео
        self.videos_list = QListWidget()
        self.videos_list.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:hover {
                background-color: #3b3b3b;
            }
        """)
        layout.addWidget(self.videos_list)
        
    def load_videos(self):
        """Загрузка списка видео из VK"""
        self.refresh_btn.setEnabled(False)
        self.thread = LoadVideosThread(self.vk_api)
        self.thread.videos_loaded.connect(self.on_videos_loaded)
        self.thread.error_occurred.connect(self.on_error)
        self.thread.start()
        
    def on_videos_loaded(self, videos):
        """Обработка загруженных видео"""
        self.videos_list.clear()
        for video in videos:
            item = QListWidgetItem(self.videos_list)
            widget = VkVideoItem(video)
            widget.edit_btn.clicked.connect(
                lambda checked, v=video: self.edit_video(v)
            )
            widget.delete_btn.clicked.connect(
                lambda checked, v=video: self.delete_video(v)
            )
            item.setSizeHint(widget.sizeHint())
            self.videos_list.addItem(item)
            self.videos_list.setItemWidget(item, widget)
            
        self.refresh_btn.setEnabled(True)
        
    def on_error(self, error_msg):
        """Обработка ошибок"""
        QMessageBox.warning(self, "Ошибка", error_msg)
        self.refresh_btn.setEnabled(True)
        
    def edit_video(self, video):
        """Редактирование видео"""
        from .dialogs.edit_video_dialog import EditVideoDialog
        
        dialog = EditVideoDialog(video, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                new_data = dialog.get_data()
                access_token = self.vk_api.get_current_token()
                
                success = self.vk_api.edit_video(
                    access_token=access_token,
                    owner_id=video['owner_id'],
                    video_id=video['id'],
                    title=new_data['title'],
                    description=new_data['description'],
                    privacy_view=new_data['privacy_view']
                )
                
                if success:
                    logger.info("Видео успешно обновлено")
                    self.load_videos()  # Перезагружаем список
                else:
                    raise ValueError("Не удалось обновить видео")
                    
            except Exception as e:
                logger.error(f"Ошибка при обновлении видео: {str(e)}")
                QMessageBox.warning(self, "Ошибка", str(e))
        
    def delete_video(self, video):
        """Удаление видео"""
        reply = QMessageBox.question(
            self,
            'Подтверждение',
            f'Вы уверены, что хотите удалить видео "{video["title"]}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                access_token = self.vk_api.get_current_token()
                success = self.vk_api.delete_video(
                    access_token=access_token,
                    owner_id=video['owner_id'],
                    video_id=video['id']
                )
                
                if success:
                    logger.info(f"Видео успешно удалено: {video['title']}")
                    self.load_videos()  # Перезагружаем список
                else:
                    raise ValueError("Не удалось удалить видео")
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении видео: {str(e)}")
                QMessageBox.warning(self, "Ошибка", str(e))

    def add_search(self):
        """Добавление поиска"""
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по названию...")
        self.search_input.textChanged.connect(self.filter_videos)
        
        search_layout.addWidget(self.search_input)
        self.layout().insertLayout(0, search_layout)
        
    def filter_videos(self, text):
        """Фильтрация видео по поиску"""
        text = text.lower()
        for i in range(self.videos_list.count()):
            item = self.videos_list.item(i)
            widget = self.videos_list.itemWidget(item)
            should_show = text in widget.title.lower()
            item.setHidden(not should_show) 