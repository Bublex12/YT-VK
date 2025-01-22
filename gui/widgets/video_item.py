from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QPixmap, QImage, QDesktopServices
from PyQt6.QtCore import QUrl
import requests
import logging
import humanize
import os
from core.settings import Settings
from .upload_worker import UploadWorker

logger = logging.getLogger(__name__)

class VideoListItem(QWidget):
    def __init__(self, title, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.parent_widget = parent  # Сохраняем ссылку на родительский виджет
        self.title = title
        self.is_uploading = False  # Флаг загрузки
        self.db = self.parent_widget.db  # Получаем доступ к БД
        
        # Получаем source_url из downloaded_videos
        video_id = os.path.basename(os.path.dirname(video_path))
        self.source_url = ""
        if video_id in self.parent_widget.downloaded_videos:
            self.source_url = self.parent_widget.downloaded_videos[video_id].get('source_url', '')
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Название видео
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        
        # Статус
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Кнопка загрузки
        self.upload_button = QPushButton("Загрузить в VK")
        self.upload_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.upload_button.clicked.connect(self.on_upload_click)
        layout.addWidget(self.upload_button)
        
        # Кнопка удаления
        self.delete_button = QPushButton("🗑")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #dc3545;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                color: #c82333;
            }
        """)
        layout.addWidget(self.delete_button)
        
        # Добавляем виджет прогресса
        from .progress_widget import ProgressWidget
        self.progress_widget = ProgressWidget()
        self.progress_widget.hide()
        layout.addWidget(self.progress_widget)
        
        # Превью видео
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(120, 68)  # 16:9 соотношение
        self.thumbnail_label.setStyleSheet("border: 1px solid #666;")
        layout.addWidget(self.thumbnail_label)
        
        # Добавляем кликабельную ссылку
        self.link_label = QLabel()
        self.link_label.setStyleSheet("""
            QLabel {
                color: #007bff;
                text-decoration: underline;
            }
            QLabel:hover {
                color: #0056b3;
            }
        """)
        self.link_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.link_label.mousePressEvent = self.open_video_url
        layout.addWidget(self.link_label)
        
        # Контейнер для информации и кнопок
        info_layout = QVBoxLayout()
        
        # Размер файла
        if os.path.exists(self.video_path):
            size = os.path.getsize(self.video_path)
            size_str = humanize.naturalsize(size)
            self.size_label = QLabel(size_str)
            self.size_label.setStyleSheet("color: #888;")
            info_layout.addWidget(self.size_label)
            
        info_layout.addStretch()
        
        # Добавляем кнопку выбора превью
        self.select_thumb_btn = QPushButton("Выбрать превью")
        self.select_thumb_btn.setFixedWidth(120)
        self.select_thumb_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        info_layout.addWidget(self.select_thumb_btn)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
        
        # Загружаем превью
        self.load_thumbnail()
        
        self.select_thumb_btn.clicked.connect(self.select_thumbnail)
        
        self.thumbnail_path = None  # Путь к выбранному превью
        
        # Проверяем, загружено ли видео
        video_info = self.db.get_video_info(self.video_path)
        if video_info:
            owner_id, video_id, vk_url = video_info
            self.link_label.setText("Открыть в VK")
            self.link_label.setToolTip(vk_url)
            self.upload_button.setEnabled(False)
            self.status_label.setText("✓ Загружено")
            self.status_label.setStyleSheet("color: green")
        
        # Добавляем прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #444;
                height: 4px;
                margin: 2px 0;
            }
            QProgressBar::chunk {
                background: #2196F3;
            }
        """)
        self.progress_bar.hide()
        self.layout().addWidget(self.progress_bar)
        
        # Кнопка повтора
        self.retry_btn = QPushButton("Повторить")
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: #d32f2f;
            }
        """)
        self.retry_btn.hide()
        self.layout().addWidget(self.retry_btn)
        
    def load_thumbnail(self):
        """Загрузка превью видео"""
        try:
            # Ищем превью в директории с видео
            video_dir = os.path.dirname(self.video_path)
            thumbnails = [f for f in os.listdir(video_dir) 
                         if f.endswith(('.jpg', '.png', '.webp'))]
            
            if thumbnails:
                thumbnail_path = os.path.join(video_dir, thumbnails[0])
                pixmap = QPixmap(thumbnail_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        120, 68,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.thumbnail_label.setPixmap(pixmap)
                    return
                    
            # Если превью не найдено, показываем заглушку
            self.thumbnail_label.setText("Нет превью")
            self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке превью: {str(e)}")
            self.thumbnail_label.setText("Ошибка")
        
    def on_upload_click(self):
        if self.is_uploading:
            if hasattr(self, 'upload_thread'):
                self.upload_thread.cancel()
        else:
            settings = Settings()
            default_group_id = settings.get('default_group_id')
            
            if default_group_id:
                # Используем группу по умолчанию
                self.start_upload(default_group_id)
            else:
                # Показываем диалог выбора группы
                from ..dialogs.group_selector import GroupSelectorDialog
                dialog = GroupSelectorDialog(self.parent_widget.vk_api, self)
                
                if dialog.exec() == GroupSelectorDialog.DialogCode.Accepted:
                    group = dialog.get_selected_group()
                    if group:
                        self.start_upload(group['id'])
                    
    def start_upload(self, group_id):
        """Начало загрузки видео"""
        self.is_uploading = True
        
        # Обновляем UI в основном потоке
        self.upload_button.setText("Отмена")
        self.status_label.setText("Подготовка...")
        self.progress_widget.show()
        self.progress_widget.start_animation()
        
        # Создаем поток для загрузки
        self.upload_thread = QThread()
        self.upload_worker = UploadWorker(
            self.parent_widget.vk_api,
            self.video_path,
            self.title,
            group_id=group_id,
            source_url=self.source_url
        )
        
        # Перемещаем worker в поток
        self.upload_worker.moveToThread(self.upload_thread)
        
        # Подключаем сигналы
        self.upload_worker.progress.connect(self.on_upload_progress)
        self.upload_worker.finished.connect(self.on_upload_finished)
        self.upload_thread.started.connect(self.upload_worker.run)
        
        # Запускаем поток
        self.upload_thread.start()
        
    def on_upload_progress(self, value):
        """Обработка прогресса загрузки"""
        self.progress_widget.set_progress(value)
        
    def on_upload_finished(self, success, result):
        """Обработка завершения загрузки"""
        self.is_uploading = False
        self.upload_button.setText("Загрузить в VK")
        self.progress_widget.hide()
        
        from PyQt6.QtWidgets import QMessageBox
        from ..styles import INFO_DIALOG_STYLE, ERROR_DIALOG_STYLE
        
        if success:
            owner_id = result.get('owner_id')
            video_id = result.get('video_id')
            if owner_id and video_id:
                video_url = f"https://vk.com/video{owner_id}_{video_id}"
                
                # Сохраняем информацию в БД
                self.db.add_uploaded_video(
                    self.video_path,
                    self.title,
                    owner_id,
                    video_id,
                    video_url
                )
                
                # Обновляем интерфейс
                self.status_label.setText("✓ Загружено")
                self.status_label.setStyleSheet("color: green")
                self.upload_button.setEnabled(False)
                self.link_label.setText("Открыть в VK")
                self.link_label.setToolTip(video_url)
                
                msg = QMessageBox()
                msg.setStyleSheet(INFO_DIALOG_STYLE)
                msg.setWindowTitle("Успех")
                msg.setText("Видео успешно загружено!")
                msg.setInformativeText(f"Ссылка на видео:\n{video_url}")
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
        else:
            self.status_label.setText("Ошибка")
            self.status_label.setStyleSheet("color: red")
            error = result.get('error', 'Неизвестная ошибка')
            
            msg = QMessageBox()
            msg.setStyleSheet(ERROR_DIALOG_STYLE)
            msg.setWindowTitle("Ошибка загрузки")
            msg.setText(str(error))
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
        
    def select_thumbnail(self):
        """Выбор файла превью"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение для превью",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.thumbnail_path = file_path
            self.select_thumb_btn.setText("✓ Превью выбрано")
            self.select_thumb_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """) 
        
    def open_video_url(self, event):
        """Открытие ссылки на видео"""
        if self.link_label.toolTip():
            QDesktopServices.openUrl(QUrl(self.link_label.toolTip())) 
        
    def set_status(self, status):
        self.status_label.setText(status)
        
    def show_progress_bar(self):
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
    def hide_progress_bar(self):
        self.progress_bar.hide()
        
    def update_progress(self, value):
        self.progress_bar.setValue(int(value))
        
    def show_retry_button(self):
        self.retry_btn.show()
        
    def hide_retry_button(self):
        self.retry_btn.hide() 