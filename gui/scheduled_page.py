from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem,
    QDateTimeEdit, QDialog, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from core.vk_api import VkApi
import logging
import json
import os

logger = logging.getLogger(__name__)

class ScheduleDialog(QDialog):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Запланировать загрузку")
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        # Выбор даты и времени
        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        form.addRow("Дата и время:", self.datetime_edit)
        
        layout.addLayout(form)
        
        # Кнопки
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        schedule_btn = QPushButton("Запланировать")
        schedule_btn.clicked.connect(self.accept)
        schedule_btn.setStyleSheet("""
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
        buttons.addWidget(schedule_btn)
        
        layout.addLayout(buttons)

class ScheduledPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vk_api = VkApi()
        self.scheduled_uploads = self.load_scheduled()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_scheduled)
        self.timer.start(60000)  # Проверка каждую минуту
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        header = QHBoxLayout()
        title = QLabel("Запланированные загрузки")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        
        layout.addLayout(header)
        
        # Список запланированных загрузок
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
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
        layout.addWidget(self.list_widget)
        
        self.refresh_list()
        
    def load_scheduled(self):
        """Загрузка запланированных загрузок"""
        try:
            if os.path.exists('scheduled_uploads.json'):
                with open('scheduled_uploads.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке запланированных загрузок: {str(e)}")
        return []
        
    def save_scheduled(self):
        """Сохранение запланированных загрузок"""
        try:
            with open('scheduled_uploads.json', 'w') as f:
                json.dump(self.scheduled_uploads, f)
        except Exception as e:
            logger.error(f"Ошибка при сохранении запланированных загрузок: {str(e)}")
            
    def add_scheduled_upload(self, video_path, upload_time):
        """Добавление новой запланированной загрузки"""
        self.scheduled_uploads.append({
            'video_path': video_path,
            'upload_time': upload_time,
            'status': 'pending'
        })
        self.save_scheduled()
        self.refresh_list()
        
    def check_scheduled(self):
        """Проверка и выполнение запланированных загрузок"""
        current_time = QDateTime.currentDateTime().toString()
        updated = False
        
        for upload in self.scheduled_uploads:
            if upload['status'] == 'pending' and upload['upload_time'] <= current_time:
                try:
                    # TODO: Добавить логику загрузки видео
                    upload['status'] = 'completed'
                    updated = True
                except Exception as e:
                    logger.error(f"Ошибка при загрузке видео: {str(e)}")
                    upload['status'] = 'failed'
                    upload['error'] = str(e)
                    updated = True
                    
        if updated:
            self.save_scheduled()
            self.refresh_list()
            
    def refresh_list(self):
        """Обновление списка запланированных загрузок"""
        try:
            # Перезагружаем список
            self.load_scheduled_uploads()
        except Exception as e:
            logger.error(f"Ошибка при обновлении списка: {str(e)}")
            
    def create_upload_item(self, upload):
        """Создание виджета для отображения запланированной загрузки"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Информация о видео
        info_layout = QVBoxLayout()
        
        # Путь к файлу
        path_label = QLabel(os.path.basename(upload['video_path']))
        path_label.setStyleSheet("color: white; font-weight: bold;")
        info_layout.addWidget(path_label)
        
        # Время загрузки и статус
        status_layout = QHBoxLayout()
        time_label = QLabel(f"Запланировано на: {upload['upload_time']}")
        time_label.setStyleSheet("color: #888;")
        status_layout.addWidget(time_label)
        
        status_colors = {
            'pending': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545'
        }
        status_texts = {
            'pending': 'Ожидает',
            'completed': 'Загружено',
            'failed': 'Ошибка'
        }
        
        status = QLabel(status_texts.get(upload['status'], 'Неизвестно'))
        status.setStyleSheet(f"color: {status_colors.get(upload['status'], '#888')};")
        status_layout.addWidget(status)
        
        info_layout.addLayout(status_layout)
        
        if upload.get('error'):
            error_label = QLabel(upload['error'])
            error_label.setStyleSheet("color: #dc3545;")
            info_layout.addWidget(error_label)
            
        layout.addLayout(info_layout)
        
        # Кнопки
        if upload['status'] == 'pending':
            cancel_btn = QPushButton("Отменить")
            cancel_btn.setStyleSheet("""
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
            cancel_btn.clicked.connect(lambda: self.cancel_upload(upload))
            layout.addWidget(cancel_btn)
            
        return widget
        
    def cancel_upload(self, upload):
        """Отмена запланированной загрузки"""
        reply = QMessageBox.question(
            self,
            'Подтверждение',
            'Вы уверены, что хотите отменить запланированную загрузку?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.scheduled_uploads.remove(upload)
            self.save_scheduled()
            self.refresh_list() 