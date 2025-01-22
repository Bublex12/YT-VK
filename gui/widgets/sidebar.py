from PyQt6.QtWidgets import QFrame, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("""
            QFrame#sidebar {
                background-color: #2b2b2b;
                border: none;
                min-width: 200px;
                max-width: 200px;
            }
            QPushButton {
                color: white;
                border: none;
                text-align: left;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
            }
            QPushButton:checked {
                background-color: #404040;
                border-left: 3px solid #007bff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Заголовок
        title = QLabel("YT → VK Uploader")
        title.setStyleSheet("""
            color: white;
            font-size: 18px;
            padding: 20px;
            background-color: #232323;
        """)
        layout.addWidget(title)
        
        # Кнопки меню
        self.menu_buttons = {}
        menu_items = {
            'download': '⬇️ Скачать видео',
            'uploads': '📤 Загрузки',
            'scheduled': '⏰ Запланированные',
            'stats': '📊 Статистика',
            'settings': '⚙️ Настройки'
        }
        
        for key, text in menu_items.items():
            btn = QPushButton(text)
            btn.setCheckable(True)
            self.menu_buttons[key] = btn
            layout.addWidget(btn)
        
        # Растягиваем пространство
        layout.addStretch()
        
        # Добавляем профиль
        from .profile_widget import ProfileWidget
        self.profile_widget = ProfileWidget()
        self.profile_widget.hide()  # Скрываем до авторизации
        layout.addWidget(self.profile_widget)
        
        # Кнопка авторизации
        self.auth_btn = QPushButton("🔑 Авторизация VK")
        self.auth_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px;
                margin: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        layout.addWidget(self.auth_btn)
        
        # Версия приложения
        version = QLabel("v1.0.0")
        version.setStyleSheet("color: #666; padding: 10px;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version) 

    def add_upload_indicator(self, title):
        """Добавление индикатора текущей загрузки"""
        if not hasattr(self, 'upload_indicators'):
            self.upload_indicators = {}
        
        indicator = QLabel(f"⏳ {title[:30]}...")
        indicator.setStyleSheet("""
            color: #4CAF50;
            padding: 5px 10px;
            font-size: 12px;
            background: #1e1e1e;
            border-radius: 3px;
            margin: 0 5px;
        """)
        
        # Вставляем перед растягивающимся пространством
        self.layout().insertWidget(self.layout().count() - 4, indicator)
        self.upload_indicators[title] = indicator
        
    def remove_upload_indicator(self, title):
        """Удаление индикатора загрузки"""
        if hasattr(self, 'upload_indicators') and title in self.upload_indicators:
            indicator = self.upload_indicators.pop(title)
            indicator.deleteLater() 