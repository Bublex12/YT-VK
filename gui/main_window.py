from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence
import logging
from core.vk_api import VkApi
from .download_page import DownloadPage
from .uploads_page import UploadsPage
from .scheduled_page import ScheduledPage
from .stats_page import StatsPage
from .settings_page import SettingsPage
from .widgets.sidebar import Sidebar

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YouTube to VK Uploader')
        self.setGeometry(100, 100, 1200, 800)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной горизонтальный layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Создаем VkApi
        self.vk_api = VkApi()
        
        # Боковое меню
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Подключаем сигналы кнопок меню
        for key, btn in self.sidebar.menu_buttons.items():
            btn.clicked.connect(lambda checked, k=key: self.on_menu_click(k))
        
        # Подключаем кнопку авторизации
        self.sidebar.auth_btn.clicked.connect(self.show_auth_dialog)
        self.sidebar.profile_widget.logout_btn.clicked.connect(self.logout)
        
        # Основная область с контентом
        self.content_area = QStackedWidget()
        main_layout.addWidget(self.content_area)
        
        # Устанавливаем соотношение размеров
        main_layout.setStretch(0, 1)  # sidebar
        main_layout.setStretch(1, 4)  # content
        
        self.init_ui()
        # Проверяем авторизацию при запуске
        QTimer.singleShot(0, self.check_auth)
        
        self.setup_shortcuts()
        
    def init_ui(self):
        # Добавляем страницы в content_area
        from .download_page import DownloadPage
        from .settings_page import SettingsPage
        from .uploads_page import UploadsPage
        from .scheduled_page import ScheduledPage
        from .stats_page import StatsPage
        
        # Создаем страницы
        self.download_page = DownloadPage()
        self.uploads_page = UploadsPage()
        self.scheduled_page = ScheduledPage()
        self.stats_page = StatsPage()
        self.settings_page = SettingsPage(vk_api=self.vk_api)
        
        # Добавляем страницы в стек
        self.content_area.addWidget(self.download_page)
        self.content_area.addWidget(self.uploads_page)
        self.content_area.addWidget(self.scheduled_page)
        self.content_area.addWidget(self.stats_page)
        self.content_area.addWidget(self.settings_page)
        
        # Активируем первую страницу
        self.sidebar.menu_buttons['download'].setChecked(True)
        self.content_area.setCurrentIndex(0)

    def on_menu_click(self, key):
        # Обновляем состояние кнопок
        for k, btn in self.sidebar.menu_buttons.items():
            btn.setChecked(k == key)
        
        # Переключаем страницу
        page_indices = {
            'download': 0,
            'uploads': 1,
            'scheduled': 2,
            'stats': 3,
            'settings': 4
        }
        
        if key in page_indices:
            self.content_area.setCurrentIndex(page_indices[key])
            logger.info(f"Переключение на страницу: {key}") 

    def check_auth(self):
        """Проверка авторизации при запуске"""
        try:
            if not self.vk_api.ensure_token():
                logger.info("Требуется авторизация")
                self.show_auth_dialog()
            else:
                # Получаем информацию о пользователе
                user_info = self.vk_api.get_user_info(self.vk_api.get_current_token())
                logger.info(f"Авторизован как: {user_info.get('first_name')} {user_info.get('last_name')}")
                
                # Обновляем интерфейс
                self.sidebar.profile_widget.update_profile(user_info)
                self.sidebar.profile_widget.show()  # Показываем виджет профиля
                self.sidebar.auth_btn.hide()  # Скрываем кнопку авторизации
                
                # Обновляем статус бар
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(
                        f"Авторизован как: {user_info.get('first_name')} {user_info.get('last_name')}"
                    )
                
        except Exception as e:
            logger.error(f"Ошибка при проверке авторизации: {str(e)}")
            self.show_auth_dialog()
            
    def show_auth_dialog(self):
        """Показ диалога авторизации"""
        try:
            auth_url = self.vk_api.get_auth_url()
            dialog = VKAuthDialog(auth_url)
            
            if dialog.exec() == VKAuthDialog.DialogCode.Accepted:
                user_info = self.vk_api.get_user_info(self.vk_api.get_current_token())
                logger.info(f"Успешная авторизация: {user_info.get('first_name')} {user_info.get('last_name')}")
                
                # Обновляем интерфейс
                self.sidebar.profile_widget.update_profile(user_info)
                self.sidebar.profile_widget.show()  # Показываем виджет профиля
                self.sidebar.auth_btn.hide()  # Скрываем кнопку авторизации
                
                # Обновляем статус бар
                if hasattr(self, 'status_bar'):
                    self.status_bar.showMessage(
                        f"Авторизован как: {user_info.get('first_name')} {user_info.get('last_name')}"
                    )
            else:
                logger.warning("Авторизация отменена пользователем")
                
        except Exception as e:
            logger.error(f"Ошибка при показе диалога авторизации: {str(e)}")
            QMessageBox.warning(self, 'Ошибка', f'Ошибка авторизации: {str(e)}')

    def logout(self):
        """Выход из аккаунта"""
        self.vk_api.token_manager.clear_token()
        self.sidebar.profile_widget.hide()
        self.sidebar.auth_btn.show()
        QMessageBox.information(
            self,
            "Успех",
            "Вы успешно вышли из аккаунта"
        ) 

    def setup_shortcuts(self):
        """Настройка горячих клавиш"""
        shortcuts = {
            'Ctrl+D': ('download', 'Скачать видео'),
            'Ctrl+U': ('uploads', 'Загрузки'),
            'Ctrl+S': ('scheduled', 'Запланированные'),
            'Ctrl+T': ('stats', 'Статистика'),
            'Ctrl+P': ('settings', 'Настройки'),
            'Ctrl+Q': (self.close, 'Выход'),
            'Ctrl+R': (self.refresh_current_page, 'Обновить'),
            'F5': (self.refresh_current_page, 'Обновить')
        }
        
        for key, (action, description) in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key), self)
            if callable(action):
                shortcut.activated.connect(action)
            else:
                shortcut.activated.connect(lambda k=action: self.on_menu_click(k)) 

    def refresh_current_page(self):
        """Обновление текущей страницы"""
        current_index = self.content_area.currentIndex()
        
        # Определяем текущую страницу и вызываем соответствующий метод обновления
        if current_index == 0:  # download page
            self.download_page.refresh_videos_list()
        elif current_index == 1:  # uploads page
            self.uploads_page.load_videos()
        elif current_index == 2:  # scheduled page
            self.scheduled_page.refresh_list()
        elif current_index == 3:  # stats page
            self.stats_page.refresh_stats()
        
        logger.info("Страница обновлена") 