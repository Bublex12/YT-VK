from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QComboBox, QPushButton,
    QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class GroupSelectorDialog(QDialog):
    def __init__(self, vk_api, parent=None):
        super().__init__(parent)
        self.vk_api = vk_api
        self.selected_group_id = None
        self.init_ui()
        self.load_groups()
        
    def init_ui(self):
        self.setWindowTitle('Выбор группы')
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Заголовок
        label = QLabel("Выберите группу для загрузки видео:")
        label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        # Комбобокс для групп
        self.group_combo = QComboBox()
        self.group_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #555;
                border-radius: 3px;
                background: #2b2b2b;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(resources/down-arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        layout.addWidget(self.group_combo)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Выбрать")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def load_groups(self):
        """Загрузка списка групп"""
        try:
            groups = self.vk_api.get_user_groups()
            if groups:
                for group in groups:
                    self.group_combo.addItem(
                        group['name'], 
                        userData={'id': group['id'], 'name': group['name']}
                    )
                self.ok_button.setEnabled(True)
            else:
                self.group_combo.addItem("Нет доступных групп")
                self.ok_button.setEnabled(False)
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке групп: {str(e)}")
            self.group_combo.addItem("Ошибка загрузки групп")
            self.ok_button.setEnabled(False)
            
    def get_selected_group(self):
        """Получение выбранной группы"""
        current_data = self.group_combo.currentData()
        if current_data:
            return current_data
        return None 