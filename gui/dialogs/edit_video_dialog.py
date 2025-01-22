from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QComboBox,
    QFormLayout, QCheckBox, QSpinBox, QGroupBox,
    QDateTimeEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QPixmap, QImage
import logging
import os

logger = logging.getLogger(__name__)

class EditVideoDialog(QDialog):
    def __init__(self, video_data, parent=None):
        super().__init__(parent)
        self.video_data = video_data
        self.thumbnail_path = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Редактирование видео")
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        
        # Устанавливаем стиль для всего диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QLineEdit, QTextEdit {
                background-color: #363636;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #007bff;
            }
            QComboBox {
                background-color: #363636;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QSpinBox {
                background-color: #363636;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
            QDateTimeEdit {
                background-color: #363636;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #404040;
                background: #363636;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #007bff;
                background: #007bff;
            }
        """)
        
        # Основная информация
        main_group = QGroupBox("Основная информация")
        form_layout = QFormLayout()
        
        # Название
        self.title_edit = QLineEdit(self.video_data.get('title', ''))
        self.title_edit.setPlaceholderText("Введите название видео")
        form_layout.addRow("Название:", self.title_edit)
        
        # Описание
        self.description_edit = QTextEdit()
        self.description_edit.setText(self.video_data.get('description', ''))
        self.description_edit.setPlaceholderText("Введите описание видео")
        self.description_edit.setMinimumHeight(100)
        form_layout.addRow("Описание:", self.description_edit)
        
        main_group.setLayout(form_layout)
        layout.addWidget(main_group)
        
        # Настройки доступа
        access_group = QGroupBox("Настройки доступа")
        access_layout = QFormLayout()
        
        # Приватность
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems([
            "Доступно всем",
            "Только друзьям",
            "Только мне"
        ])
        current_privacy = self.video_data.get('privacy_view', 'all')
        privacy_map = {'all': 0, 'friends': 1, 'private': 2}
        self.privacy_combo.setCurrentIndex(privacy_map.get(current_privacy, 0))
        access_layout.addRow("Приватность:", self.privacy_combo)
        
        # Комментарии
        self.comments_enabled = QCheckBox("Разрешить комментарии")
        self.comments_enabled.setChecked(self.video_data.get('comments_enabled', True))
        access_layout.addRow("", self.comments_enabled)
        
        # Отображение в поиске
        self.searchable = QCheckBox("Отображать в поиске")
        self.searchable.setChecked(self.video_data.get('no_search', False))
        access_layout.addRow("", self.searchable)
        
        access_group.setLayout(access_layout)
        layout.addWidget(access_group)
        
        # Дополнительные настройки
        extra_group = QGroupBox("Дополнительные настройки")
        extra_layout = QFormLayout()
        
        # Возрастное ограничение
        self.age_restriction = QSpinBox()
        self.age_restriction.setRange(0, 21)
        self.age_restriction.setValue(self.video_data.get('age_restriction', 0))
        self.age_restriction.setSpecialValueText("Без ограничений")
        extra_layout.addRow("Возрастное ограничение:", self.age_restriction)
        
        # Отложенная публикация
        self.publish_later = QCheckBox("Отложенная публикация")
        self.publish_later.setChecked(False)
        self.publish_later.toggled.connect(self.toggle_publish_date)
        extra_layout.addRow("", self.publish_later)
        
        # Дата публикации
        self.publish_date = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.publish_date.setEnabled(False)
        self.publish_date.setMinimumDateTime(QDateTime.currentDateTime())
        self.publish_date.setCalendarPopup(True)
        extra_layout.addRow("Дата публикации:", self.publish_date)
        
        extra_group.setLayout(extra_layout)
        layout.addWidget(extra_group)
        
        # Добавляем группу для превью
        preview_group = QGroupBox("Превью")
        preview_layout = QVBoxLayout()
        
        # Контейнер для превью
        self.preview_container = QLabel()
        self.preview_container.setFixedSize(320, 180)  # 16:9
        self.preview_container.setStyleSheet("""
            QLabel {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)
        self.preview_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Загружаем текущее превью если есть
        if self.video_data.get('thumb_url'):
            self.load_remote_thumbnail(self.video_data['thumb_url'])
        else:
            self.preview_container.setText("Нет превью")
            
        preview_layout.addWidget(self.preview_container)
        
        # Информационное сообщение
        info_label = QLabel("VK API не поддерживает изменение превью для существующих видео")
        info_label.setStyleSheet("""
            color: #ffc107;
            font-style: italic;
            padding: 5px;
        """)
        info_label.setWordWrap(True)
        preview_layout.addWidget(info_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
    def toggle_publish_date(self, checked):
        """Включение/выключение поля даты публикации"""
        self.publish_date.setEnabled(checked)
        
    def select_thumbnail(self):
        """Выбор файла превью"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.load_local_thumbnail(file_path)
            
    def load_local_thumbnail(self, file_path):
        """Загрузка локального превью"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    320, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_container.setPixmap(scaled_pixmap)
                self.thumbnail_path = file_path
            else:
                raise ValueError("Не удалось загрузить изображение")
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке превью: {str(e)}")
            self.preview_container.setText("Ошибка загрузки")
            
    def load_remote_thumbnail(self, url):
        """Загрузка превью по URL"""
        try:
            import requests
            response = requests.get(url)
            response.raise_for_status()
            
            image = QImage()
            image.loadFromData(response.content)
            
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                scaled_pixmap = pixmap.scaled(
                    320, 180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_container.setPixmap(scaled_pixmap)
            else:
                raise ValueError("Не удалось загрузить изображение")
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке превью: {str(e)}")
            self.preview_container.setText("Ошибка загрузки")
            
    def get_data(self):
        """Получение обновленных данных"""
        privacy_map = {0: 'all', 1: 'friends', 2: 'private'}
        data = {
            'title': self.title_edit.text(),
            'description': self.description_edit.toPlainText(),
            'privacy_view': privacy_map[self.privacy_combo.currentIndex()],
            'comments_enabled': self.comments_enabled.isChecked(),
            'no_search': not self.searchable.isChecked(),
            'age_restriction': self.age_restriction.value()
        }
        
        if self.publish_later.isChecked():
            data['publish_date'] = self.publish_date.dateTime().toString()
            
        # Добавляем путь к превью если оно было изменено
        if self.thumbnail_path:
            data['thumbnail_path'] = self.thumbnail_path
            
        return data 