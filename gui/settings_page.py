from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QLineEdit, QFileDialog,
    QGroupBox, QFormLayout, QCheckBox
)
from PyQt6.QtCore import Qt
from core.config import OUTPUT_DIR, VK_GROUP_ID
from core.settings import Settings
import logging
import json
import os

logger = logging.getLogger(__name__)

class SettingsPage(QWidget):
    def __init__(self, vk_api, parent=None):
        super().__init__(parent)
        self.vk_api = vk_api
        self.settings = Settings()
        self.init_ui()
        self.load_groups()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Группа настроек видео
        video_group = QGroupBox("Настройки видео")
        video_layout = QFormLayout()
        
        # Качество видео по умолчанию
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "1080p (Full HD)",
            "720p (HD)",
            "480p (SD)",
            "360p",
            "Максимальное доступное"
        ])
        self.quality_combo.setCurrentText(
            self.settings.get('default_quality', "1080p (Full HD)")
        )
        video_layout.addRow("Качество по умолчанию:", self.quality_combo)
        
        # Директория сохранения
        dir_layout = QHBoxLayout()
        self.dir_edit = QLineEdit(self.settings.get('output_dir', OUTPUT_DIR))
        self.dir_edit.setReadOnly(True)
        dir_layout.addWidget(self.dir_edit)
        
        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(self.browse_btn)
        
        video_layout.addRow("Папка для сохранения:", dir_layout)
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        
        # Группа настроек VK
        vk_group = QGroupBox("Настройки ВКонтакте")
        vk_layout = QVBoxLayout()
        
        # Выбор группы по умолчанию
        group_layout = QHBoxLayout()
        group_label = QLabel("Группа по умолчанию:")
        self.group_combo = QComboBox()
        self.group_combo.setMinimumWidth(300)
        self.group_combo.currentIndexChanged.connect(self.on_group_changed)
        
        group_layout.addWidget(group_label)
        group_layout.addWidget(self.group_combo)
        group_layout.addStretch()
        vk_layout.addLayout(group_layout)
        
        # Кнопка обновления списка групп
        refresh_button = QPushButton("Обновить список групп")
        refresh_button.clicked.connect(self.load_groups)
        vk_layout.addWidget(refresh_button)
        
        vk_group.setLayout(vk_layout)
        layout.addWidget(vk_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_settings)
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
        layout.addStretch()
        
    def load_groups(self):
        """Загрузка списка групп"""
        try:
            self.group_combo.clear()
            self.group_combo.addItem("Не выбрано", userData=None)
            
            groups = self.vk_api.get_user_groups()
            if groups:
                for group in groups:
                    self.group_combo.addItem(
                        group['name'], 
                        userData={'id': group['id'], 'name': group['name']}
                    )
                    
                # Выбираем сохраненную группу
                default_group_id = self.settings.get('default_group_id')
                if default_group_id:
                    for i in range(self.group_combo.count()):
                        data = self.group_combo.itemData(i)
                        if data and data['id'] == default_group_id:
                            self.group_combo.setCurrentIndex(i)
                            break
                            
        except Exception as e:
            logger.error(f"Ошибка при загрузке групп: {str(e)}")
            
    def on_group_changed(self, index):
        """Обработка выбора группы"""
        data = self.group_combo.currentData()
        if data:
            self.settings.set('default_group_id', data['id'])
            self.settings.set('default_group_name', data['name'])
        else:
            self.settings.set('default_group_id', None)
            self.settings.set('default_group_name', None)
        
    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек: {str(e)}")
        return {}
        
    def save_settings(self):
        """Сохранение настроек в файл"""
        try:
            settings = {
                'default_quality': self.quality_combo.currentText(),
                'output_dir': self.dir_edit.text(),
                'default_group_id': self.settings.get('default_group_id'),
                'default_group_name': self.settings.get('default_group_name')
            }
            
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            logger.info("Настройки успешно сохранены")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {str(e)}")
            
    def browse_directory(self):
        """Выбор директории для сохранения"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения видео",
            self.dir_edit.text()
        )
        if dir_path:
            self.dir_edit.setText(dir_path) 