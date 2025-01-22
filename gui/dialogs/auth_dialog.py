from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
import logging
import re

logger = logging.getLogger(__name__)

class AuthWebPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_data = {}
        
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        url_str = url.toString()
        logger.debug(f"Navigation request: {url_str}")
        
        if 'blank.html#' in url_str:
            try:
                # Извлекаем токен и другие параметры из URL
                fragment = url.fragment()
                params = dict(item.split('=') for item in fragment.split('&'))
                self.auth_data = params
                logger.info("Получены данные авторизации")
                
                # Находим родительский диалог
                dialog = self.parent().window()
                if isinstance(dialog, VKAuthDialog):
                    # Используем QTimer для безопасного вызова в основном потоке
                    QTimer.singleShot(0, lambda: dialog.handle_auth_success(params))
                
            except Exception as e:
                logger.error(f"Ошибка при обработке данных авторизации: {str(e)}")
            return False
        return True
        
    def javaScriptConsoleMessage(self, level, message, line, source):
        try:
            logger.debug(f"JS Console: {message} (line {line}, source: {source})")
        except Exception as e:
            logger.error(f"Ошибка при логировании JS сообщения: {str(e)}")

class VKAuthDialog(QDialog):
    auth_complete = pyqtSignal(dict)
    
    def __init__(self, auth_url, parent=None):
        super().__init__(parent)
        self.auth_url = auth_url
        self.auth_completed = False
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Авторизация ВКонтакте")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #363636;
                height: 2px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Веб-представление для авторизации
        self.web_view = QWebEngineView(self)  # Указываем родителя
        self.web_page = AuthWebPage(self.web_view)
        self.web_view.setPage(self.web_page)
        
        # Отслеживаем загрузку
        self.web_view.loadStarted.connect(self.on_load_started)
        self.web_view.loadProgress.connect(self.progress_bar.setValue)
        self.web_view.loadFinished.connect(self.on_load_finished)
        
        # Загружаем страницу авторизации
        logger.debug(f"Загрузка страницы авторизации: {self.auth_url}")
        self.web_view.setUrl(QUrl(self.auth_url))
        
        layout.addWidget(self.web_view)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
    def handle_auth_success(self, auth_data):
        """Обработка успешной авторизации"""
        if not self.auth_completed:  # Проверяем, не была ли уже завершена авторизация
            self.auth_completed = True
            logger.info("Авторизация завершена успешно")
            self.auth_complete.emit(auth_data)
            self.accept()
        
    def on_load_started(self):
        """Начало загрузки страницы"""
        logger.debug("Начало загрузки страницы")
        self.progress_bar.setVisible(True)
        
    def on_load_finished(self, success):
        """Завершение загрузки страницы"""
        logger.debug(f"Загрузка страницы завершена: {'успешно' if success else 'с ошибкой'}")
        self.progress_bar.setVisible(False)
        
        # Показываем ошибку только если это не blank.html и авторизация не завершена
        current_url = self.web_view.url().toString()
        if not success and 'blank.html' not in current_url and not self.auth_completed:
            self.show_error("Не удалось загрузить страницу авторизации")
        
    def show_error(self, message):
        """Показ ошибки"""
        error_label = QLabel(message)
        error_label.setStyleSheet("""
            QLabel {
                color: #dc3545;
                padding: 10px;
                background: #2b2b2b;
                border: 1px solid #dc3545;
                border-radius: 4px;
            }
        """)
        self.layout().insertWidget(1, error_label) 