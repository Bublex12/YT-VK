from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, 
    QPushButton, QVBoxLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage
import requests
import logging

logger = logging.getLogger(__name__)

class ProfileWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Аватар
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(32, 32)
        self.avatar_label.setStyleSheet("""
            QLabel {
                background-color: #363636;
                border-radius: 16px;
            }
        """)
        layout.addWidget(self.avatar_label)
        
        # Информация о пользователе
        info_layout = QVBoxLayout()
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet("color: white; font-weight: bold;")
        info_layout.addWidget(self.name_label)
        
        layout.addLayout(info_layout)
        
        # Кнопка выхода
        self.logout_btn = QPushButton("Выйти")
        self.logout_btn.setStyleSheet("""
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
        layout.addWidget(self.logout_btn)
        
        layout.addStretch()
        
    def update_profile(self, user_info):
        """Обновление информации профиля"""
        self.name_label.setText(f"{user_info.get('first_name')} {user_info.get('last_name')}")
        
        # Если есть фото профиля
        photo_url = user_info.get('photo_50')
        if photo_url:
            # Здесь можно добавить загрузку и отображение фото профиля
            pass

        try:
            # Загружаем аватар
            if photo_url:
                response = requests.get(photo_url)
                response.raise_for_status()
                
                image = QImage()
                image.loadFromData(response.content)
                
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    # Делаем аватарку круглой
                    rounded = QPixmap(pixmap.size())
                    rounded.fill(Qt.GlobalColor.transparent)
                    
                    pixmap = pixmap.scaled(
                        32, 32,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.avatar_label.setPixmap(pixmap)
                    
        except Exception as e:
            logger.error(f"Ошибка при обновлении профиля: {str(e)}") 