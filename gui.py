import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QLineEdit, QPushButton, QProgressBar, 
    QTextEdit, QMessageBox, QListWidget, QHBoxLayout,
    QFrame, QGridLayout, QScrollArea, QTableWidget, QHeaderView,
    QTabWidget, QTableWidgetItem, QDialog, QCheckBox, QListWidgetItem,
    QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor
from main import (
    download_youtube_video, get_video_info, logger, 
    download_only_thumbnail, search_youtube_videos, db,  # Добавляем импорт db
    check_ffmpeg, get_available_formats, get_channel_videos
)
import logging
import traceback
import requests
from datetime import datetime, timedelta
from database import VideoDatabase

class DownloadWorker(QThread):
    finished = pyqtSignal(bool, str, str, str)
    progress = pyqtSignal(str, float)
    
    def __init__(self, url, format_id=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self._is_running = True
    
    def run(self):
        try:
            handler = WorkerLogHandler(self.progress)
            handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(handler)
            
            try:
                if not self._is_running:
                    return
                    
                logger.debug(f"Запуск скачивания с URL: {self.url}")
                video_path, thumbnail_path = download_youtube_video(
                    self.url, 
                    format_id=self.format_id
                )
                if self._is_running:
                    self.finished.emit(True, video_path, thumbnail_path or "", self.url)
            except Exception as e:
                if self._is_running:
                    logger.error(f"Ошибка при скачивании: {str(e)}")
                    logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
                    self.finished.emit(False, str(e), "", self.url)
            finally:
                logger.removeHandler(handler)
        except Exception as e:
            if self._is_running:
                logger.error(f"Критическая ошибка: {str(e)}")
                logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
                self.finished.emit(False, str(e), "", self.url)
    
    def quit(self):
        self._is_running = False
        super().quit()

class WorkerLogHandler(logging.Handler):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        
    def emit(self, record):
        msg = self.format(record)
        try:
            # Проверяем различные форматы сообщений о прогрессе
            if '[download]' in msg:
                # Формат: [download]   x.x% of y.yMiB at z.zMiB/s
                if '%' in msg and 'of' in msg and 'at' in msg:
                    percent_str = msg.split()[1].replace('%', '')
                    try:
                        percent = float(percent_str)
                        self.signal.emit(msg, percent)
                        return
                    except ValueError:
                        pass
                
                # Формат: [download] 100% of x.xMiB in mm:ss at y.yMiB/s
                elif '100%' in msg:
                    self.signal.emit(msg, 100.0)
                    return
                
                # Формат: [download] Destination:
                elif 'Destination:' in msg:
                    self.signal.emit(msg, 0.0)
                    return
                
                # Формат: [download] Downloading video ...
                elif 'Downloading' in msg:
                    self.signal.emit(msg, 0.0)
                    return
            
            # Все остальные сообщения отправляем без процента
            self.signal.emit(msg, -1)
            
        except Exception as e:
            print(f"Error parsing progress: {e} in message: {msg}")
            self.signal.emit(msg, -1)

class LogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        self.text_widget.append(msg)

class VideoInfoWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QGridLayout(self)
        
        # Создаем и настраиваем labels
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 180)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.uploader_label = QLabel()
        self.duration_label = QLabel()
        self.views_label = QLabel()
        self.date_label = QLabel()
        
        # Размещаем элементы
        layout.addWidget(self.thumbnail_label, 0, 0, 1, 2)
        layout.addWidget(self.title_label, 1, 0, 1, 2)
        layout.addWidget(self.uploader_label, 2, 0)
        layout.addWidget(self.duration_label, 2, 1)
        layout.addWidget(self.views_label, 3, 0)
        layout.addWidget(self.date_label, 3, 1)
        
        self.hide()  # Скрываем виджет по умолчанию
        
    def update_info(self, info: dict):
        # Загружаем и отображаем превью
        if info['thumbnail']:
            try:
                response = requests.get(info['thumbnail'])
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                self.thumbnail_label.setPixmap(pixmap)
            except:
                self.thumbnail_label.setText("Превью недоступно")
        
        # Обновляем информацию
        self.title_label.setText(info['title'])
        self.uploader_label.setText(f"Автор: {info['uploader']}")
        
        # Форматируем длительность
        duration = timedelta(seconds=info['duration'])
        duration_str = str(duration).split('.')[0]  # Убираем миллисекунды
        self.duration_label.setText(f"Длительность: {duration_str}")
        
        # Форматируем просмотры
        views = "{:,}".format(info['view_count']).replace(',', ' ')
        self.views_label.setText(f"Просмотры: {views}")
        
        # Форматируем дату
        try:
            date = datetime.strptime(info['upload_date'], '%Y%m%d')
            date_str = date.strftime('%d.%m.%Y')
            self.date_label.setText(f"Дата: {date_str}")
        except:
            self.date_label.setText("Дата: Неизвестно")
        
        self.show()

class ThumbnailDownloadWorker(QThread):
    finished = pyqtSignal(bool, str, str)  # success, path, url
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        
    def run(self):
        try:
            thumbnail_path = download_only_thumbnail(self.url)
            if thumbnail_path:
                self.finished.emit(True, thumbnail_path, self.url)
            else:
                self.finished.emit(False, "Не удалось скачать превью", self.url)
        except Exception as e:
            self.finished.emit(False, str(e), self.url)

class SearchTab(QWidget):
    video_selected = pyqtSignal(str)  # Сигнал для передачи URL в основную вкладку
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Добавляем лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.setup_logging()
        
        # Поисковая панель
        search_panel = QGridLayout()
        
        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите поисковый запрос")
        search_panel.addWidget(QLabel("Поиск:"), 0, 0)
        search_panel.addWidget(self.search_input, 0, 1, 1, 2)
        
        # Минимальное количество просмотров
        self.views_input = QLineEdit()
        self.views_input.setPlaceholderText("1000")
        search_panel.addWidget(QLabel("Мин. просмотров:"), 1, 0)
        search_panel.addWidget(self.views_input, 1, 1)
        
        # Количество результатов
        self.results_count = QLineEdit()
        self.results_count.setPlaceholderText("50")
        search_panel.addWidget(QLabel("Кол-во результатов:"), 2, 0)
        search_panel.addWidget(self.results_count, 2, 1)
        
        # Исключаемые слова
        self.excluded_words = QLineEdit()
        self.excluded_words.setPlaceholderText("Слова через запятую")
        search_panel.addWidget(QLabel("Исключить слова:"), 3, 0)
        search_panel.addWidget(self.excluded_words, 3, 1, 1, 2)
        
        # Кнопка поиска
        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.search_videos)
        search_panel.addWidget(self.search_button, 2, 2)
        
        layout.addLayout(search_panel)
        
        # Таблица результатов
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)  # Добавляем колонку для превью
        self.results_table.setHorizontalHeaderLabels([
            "Превью",
            "Название", 
            "Просмотры", 
            "Автор",
            "Описание",
            ""  # Колонка для кнопки
        ])
        
        # Настраиваем ширину колонок
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Превью
        self.results_table.setColumnWidth(0, 160)  # Ширина колонки превью
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Название
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Просмотры
        self.results_table.setColumnWidth(2, 100)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # Автор
        self.results_table.setColumnWidth(3, 150)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Описание
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Кнопка
        self.results_table.setColumnWidth(5, 40)
        
        # Устанавливаем высоту строк для превью
        self.results_table.verticalHeader().setDefaultSectionSize(90)
        
        layout.addWidget(self.results_table)
        
        # Добавляем лог в конец layout
        log_label = QLabel("Лог поиска:")
        layout.addWidget(log_label)
        layout.addWidget(self.log_text)
        
        # Добавляем обработчик двойного клика по строке таблицы
        self.results_table.itemDoubleClicked.connect(self.show_video_details)
        
        # Стилизация
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
    
    def setup_logging(self):
        """Настройка логирования"""
        handler = LogHandler(self.log_text)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)
    
    def search_videos(self):
        self.log_text.clear()  # Очищаем лог перед новым поиском
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Внимание", "Введите поисковый запрос")
            return
        
        try:
            min_views = int(self.views_input.text() or "0")
        except ValueError as e:
            logger.error(f"Некорректное значение минимальных просмотров: {str(e)}")
            QMessageBox.warning(self, "Внимание", "Некорректное значение минимальных просмотров")
            return
            
        try:
            max_results = int(self.results_count.text() or "50")
            if max_results <= 0:
                raise ValueError("Количество результатов должно быть положительным")
        except ValueError as e:
            logger.error(f"Некорректное количество результатов: {str(e)}")
            QMessageBox.warning(self, "Внимание", f"Некорректное количество результатов: {str(e)}")
            return
            
        excluded = [w.strip() for w in self.excluded_words.text().split(',') if w.strip()]
        
        # Показываем индикатор загрузки
        self.search_button.setEnabled(False)
        self.search_button.setText("Поиск...")
        QApplication.processEvents()
        
        try:
            logger.info(f"Начало поиска. Запрос: '{query}', мин. просмотров: {min_views}, "
                       f"макс. результатов: {max_results}, исключения: {excluded}")
            videos = search_youtube_videos(query, min_views, excluded, max_results)
            logger.info(f"Поиск завершен. Найдено видео: {len(videos)}")
            self.display_results(videos)
        except Exception as e:
            logger.error(f"Ошибка при поиске: {str(e)}")
            logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при поиске: {str(e)}")
        finally:
            self.search_button.setEnabled(True)
            self.search_button.setText("Найти")
    
    def create_add_button(self, url):
        """Создание кнопки добавления с правильной привязкой URL"""
        add_button = QPushButton("➕")
        add_button.setToolTip("Добавить в очередь загрузки")
        add_button.clicked.connect(lambda _, u=url: self.video_selected.emit(u))
        add_button.setProperty('url', url)  # Сохраняем URL в свойстве кнопки
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                min-width: 30px;
                max-width: 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        return add_button
    
    def create_thumbnail_label(self, thumbnail_url):
        """Создание виджета для превью"""
        label = QLabel()
        label.setFixedSize(160, 90)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url)
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(pixmap)
            except:
                label.setText("Нет превью")
        else:
            label.setText("Нет превью")
            
        return label

    def display_results(self, videos):
        try:
            self.results_table.setRowCount(len(videos))
            logger.debug(f"Отображение {len(videos)} результатов")
            
            for row, video in enumerate(videos):
                try:
                    # Превью
                    thumbnail_label = self.create_thumbnail_label(video.get('thumbnail'))
                    self.results_table.setCellWidget(row, 0, thumbnail_label)
                    
                    # Название
                    title_item = QTableWidgetItem(video['title'] or "Без названия")
                    title_item.setToolTip(video['title'] or "Без названия")
                    self.results_table.setItem(row, 1, title_item)
                    
                    # Просмотры
                    views = QTableWidgetItem(f"{video['views']:,}".replace(',', ' '))
                    views.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.results_table.setItem(row, 2, views)
                    
                    # Автор
                    author_item = QTableWidgetItem(video['uploader'] or "Неизвестно")
                    author_item.setToolTip(video['uploader'] or "Неизвестно")
                    self.results_table.setItem(row, 3, author_item)
                    
                    # Описание
                    description = video.get('description') or "Нет описания"
                    if description and len(description) > 200:
                        description = description[:197] + "..."
                    desc_item = QTableWidgetItem(description)
                    desc_item.setToolTip(video.get('description') or "Нет описания")
                    self.results_table.setItem(row, 4, desc_item)
                    
                    # Кнопка добавления
                    add_button = self.create_add_button(video['url'])
                    self.results_table.setCellWidget(row, 5, add_button)
                    
                except Exception as e:
                    logger.error(f"Ошибка при отображении видео {row}: {str(e)}")
                    logger.debug(f"Данные видео: {video}")
                    # Заполняем ячейки значениями по умолчанию
                    self.results_table.setCellWidget(row, 0, QLabel("Ошибка"))
                    for col, default in enumerate(["Ошибка загрузки", "0", "Неизвестно", "Ошибка загрузки данных"], 1):
                        self.results_table.setItem(row, col, QTableWidgetItem(default))
                    error_button = QPushButton("❌")
                    error_button.setEnabled(False)
                    self.results_table.setCellWidget(row, 5, error_button)
                    continue
            
            logger.info("Результаты успешно отображены")
            
        except Exception as e:
            logger.error(f"Ошибка при отображении результатов: {str(e)}")
            logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
            raise

    def show_video_details(self, item):
        row = item.row()
        url = self.results_table.cellWidget(row, 5).property('url')  # Сохраняем URL в свойстве кнопки
        try:
            video_info = get_video_info(url)
            dialog = VideoDetailsDialog(video_info, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить информацию о видео:\n{str(e)}")

class VideoDetailsDialog(QDialog):
    def __init__(self, video_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Информация о видео")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Превью
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(480, 270)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        layout.addWidget(self.thumbnail_label)
        
        # Загружаем превью
        if video_info.get('thumbnail'):
            try:
                response = requests.get(video_info['thumbnail'])
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaled(480, 270, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                self.thumbnail_label.setPixmap(pixmap)
            except:
                self.thumbnail_label.setText("Превью недоступно")
        
        # Информация о видео
        info_layout = QGridLayout()
        
        # Название
        title_label = QLabel("<b>Название:</b>")
        title_text = QLabel(video_info.get('title', 'Нет названия'))
        title_text.setWordWrap(True)
        info_layout.addWidget(title_label, 0, 0)
        info_layout.addWidget(title_text, 0, 1)
        
        # URL
        url_label = QLabel("<b>URL:</b>")
        url_text = QLineEdit(video_info.get('url', ''))
        url_text.setReadOnly(True)
        copy_button = QPushButton("Копировать")
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(url_text.text()))
        info_layout.addWidget(url_label, 1, 0)
        info_layout.addWidget(url_text, 1, 1)
        info_layout.addWidget(copy_button, 1, 2)
        
        # Автор
        author_label = QLabel("<b>Автор:</b>")
        author_text = QLabel(video_info.get('uploader', 'Неизвестно'))
        info_layout.addWidget(author_label, 2, 0)
        info_layout.addWidget(author_text, 2, 1)
        
        # Просмотры
        views_label = QLabel("<b>Просмотры:</b>")
        views = "{:,}".format(video_info.get('views', 0)).replace(',', ' ')
        views_text = QLabel(views)
        info_layout.addWidget(views_label, 3, 0)
        info_layout.addWidget(views_text, 3, 1)
        
        # Длительность
        duration_label = QLabel("<b>Длительность:</b>")
        duration = str(timedelta(seconds=video_info.get('duration', 0))).split('.')[0]
        duration_text = QLabel(duration)
        info_layout.addWidget(duration_label, 4, 0)
        info_layout.addWidget(duration_text, 4, 1)
        
        # Дата загрузки
        date_label = QLabel("<b>Дата загрузки:</b>")
        upload_date = video_info.get('upload_date', '')
        if upload_date:
            try:
                date = datetime.strptime(upload_date, '%Y%m%d')
                date_str = date.strftime('%d.%m.%Y')
            except:
                date_str = upload_date
        else:
            date_str = 'Неизвестно'
        date_text = QLabel(date_str)
        info_layout.addWidget(date_label, 5, 0)
        info_layout.addWidget(date_text, 5, 1)
        
        layout.addLayout(info_layout)
        
        # Описание
        description_label = QLabel("<b>Описание:</b>")
        layout.addWidget(description_label)
        
        description_text = QTextEdit()
        description_text.setPlainText(video_info.get('description', 'Нет описания'))
        description_text.setReadOnly(True)
        description_text.setMinimumHeight(100)
        layout.addWidget(description_text)
        
        # Кнопка закрытия
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                font-size: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)

class QualitySelectDialog(QDialog):
    def __init__(self, formats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор качества")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Добавляем предупреждение, если нет форматов со звуком
        if not any(f['has_audio'] for f in formats):
            warning_label = QLabel("⚠️ Внимание: это видео не содержит звуковой дорожки!")
            warning_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(warning_label)
        
        # Добавляем легенду
        legend = QLabel("🔊 - со звуком, 🔇 - без звука")
        legend.setStyleSheet("color: gray;")
        layout.addWidget(legend)
        
        # Список форматов
        self.format_list = QListWidget()
        for fmt in formats:
            item = QListWidgetItem(fmt['display'])
            # Выделяем форматы без звука серым цветом
            if not fmt['has_audio']:
                item.setForeground(QColor('gray'))
            self.format_list.addItem(item)
        self.format_list.setCurrentRow(0)
        layout.addWidget(self.format_list)
        
        # Кнопки
        buttons = QHBoxLayout()
        
        ok_button = QPushButton("Скачать")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        
        self.selected_format = formats[0] if formats else None
        
        self.format_list.currentRowChanged.connect(
            lambda idx: setattr(self, 'selected_format', formats[idx])
        )

class VideoDownloaderApp(QMainWindow):
    MAX_CONCURRENT_DOWNLOADS = 3  # Максимальное количество одновременных загрузок
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setMinimumSize(800, 600)
        
        # Инициализация переменных
        self.active_downloads = {}
        self.download_queue = []
        self.ffmpeg_checked = False
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Вкладка загрузки
        self.download_tab = self.setup_download_tab()
        self.tabs.addTab(self.download_tab, "Загрузка")
        
        # Вкладка поиска
        self.search_tab = SearchTab()
        self.search_tab.video_selected.connect(self.add_url_to_queue)
        self.tabs.addTab(self.search_tab, "Поиск")
        
        # Вкладка канала
        self.channel_tab = ChannelTab()
        self.channel_tab.video_selected.connect(self.add_url_to_queue)
        self.tabs.addTab(self.channel_tab, "Канал")
        
        # Вкладка истории
        self.history_tab = self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "История")
        
        # Настройка логирования
        self.setup_logging()
        
        # Добавляем обработчик закрытия окна
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

    def setup_download_tab(self):
        """Настройка вкладки загрузки"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Поле ввода URL
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Введите ссылку на видео YouTube")
        self.url_input.textChanged.connect(self.on_url_changed)
        input_layout.addWidget(self.url_input)
        
        # Кнопка добавления
        self.add_button = QPushButton("Добавить в очередь")
        self.add_button.clicked.connect(lambda: self.add_url_to_queue(self.url_input.text()))
        input_layout.addWidget(self.add_button)
        
        # Добавляем input_layout в основной layout
        layout.addLayout(input_layout)
        
        # Виджет информации о видео
        self.info_widget = VideoInfoWidget()
        layout.addWidget(self.info_widget)
        
        # Таблица URL для загрузки
        self.url_table = QTableWidget()
        self.url_table.setColumnCount(4)
        self.url_table.setHorizontalHeaderLabels([
            "URL", "Качество", "Статус", "Действия"
        ])
        
        # Настройка колонок
        self.url_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.url_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.url_table.setColumnWidth(1, 250)
        self.url_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.url_table.setColumnWidth(2, 150)
        self.url_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.url_table.setColumnWidth(3, 100)
        
        layout.addWidget(self.url_table)
        
        # Кнопки действий
        buttons_layout = QHBoxLayout()
        
        # Кнопки для работы с файлом
        file_buttons_layout = QHBoxLayout()
        
        self.load_file_button = QPushButton("Загрузить из файла")
        self.load_file_button.clicked.connect(self.load_urls_from_file)
        file_buttons_layout.addWidget(self.load_file_button)
        
        self.save_file_button = QPushButton("Сохранить в файл")
        self.save_file_button.clicked.connect(self.save_urls_to_file)
        file_buttons_layout.addWidget(self.save_file_button)
        
        buttons_layout.addLayout(file_buttons_layout)
        buttons_layout.addStretch()
        
        # Кнопка скачивания
        self.download_button = QPushButton("Скачать все")
        self.download_button.clicked.connect(self.start_downloads)
        self.download_button.setEnabled(False)
        buttons_layout.addWidget(self.download_button)
        
        # Кнопка скачивания превью
        self.thumb_button = QPushButton("Скачать превью")
        self.thumb_button.clicked.connect(self.download_thumbnail)
        buttons_layout.addWidget(self.thumb_button)
        
        layout.addLayout(buttons_layout)
        
        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        return widget

    def add_url_to_queue(self, url):
        """Добавление URL в очередь"""
        try:
            # Проверяем, нет ли уже такого URL
            for row in range(self.url_table.rowCount()):
                if self.url_table.item(row, 0).text() == url:
                    logger.warning(f"URL уже в списке: {url}")
                    return

            # Получаем форматы для видео
            formats = get_available_formats(url)
            
            # Создаем новую строку
            row = self.url_table.rowCount()
            self.url_table.insertRow(row)
            
            # URL
            url_item = QTableWidgetItem(url)
            self.url_table.setItem(row, 0, url_item)
            
            # Выпадающий список форматов
            format_combo = QComboBox()
            for fmt in formats:
                format_combo.addItem(fmt['display'], fmt['format_id'])
            
            # Выбираем формат 1080p со звуком по умолчанию
            default_index = -1
            for i in range(format_combo.count()):
                display = format_combo.itemText(i)
                if "1920x1080" in display and "🔊" in display:
                    default_index = i
                    break
            if default_index != -1:
                format_combo.setCurrentIndex(default_index)
            
            self.url_table.setCellWidget(row, 1, format_combo)
            
            # Прогресс-бар
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            progress_bar.setValue(0)
            progress_bar.setFormat('В очереди')
            progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    border-radius: 2px;
                }
            """)
            self.url_table.setCellWidget(row, 2, progress_bar)
            
            # Кнопка удаления
            delete_button = QPushButton("❌")
            delete_button.clicked.connect(lambda: self.remove_url(row))
            delete_button.setMaximumWidth(50)
            
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.addWidget(delete_button)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.url_table.setCellWidget(row, 3, button_widget)
            
            self.download_button.setEnabled(True)
            logger.info(f"Добавлен URL: {url}")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении URL: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить URL:\n{str(e)}")

    def remove_url(self, row):
        """Удаление URL из очереди"""
        self.url_table.removeRow(row)
        if self.url_table.rowCount() == 0:
            self.download_button.setEnabled(False)

    def start_downloads(self):
        """Начало загрузки всех видео"""
        try:
            for row in range(self.url_table.rowCount()):
                url = self.url_table.item(row, 0).text()
                format_combo = self.url_table.cellWidget(row, 1)
                format_id = format_combo.currentData()
                
                if url not in self.active_downloads and url not in self.download_queue:
                    self.download_queue.append((url, format_id))
            
            self.process_queue()
            
        except Exception as e:
            logger.error(f"Ошибка при запуске загрузок: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось начать загрузку:\n{str(e)}")

    def update_download_status(self, row, status):
        """Обновление статуса загрузки"""
        if 0 <= row < self.url_table.rowCount():
            status_item = QTableWidgetItem(status)
            self.url_table.setItem(row, 2, status_item)

    def process_queue(self):
        """Обработка очереди загрузок"""
        try:
            # Запускаем новые загрузки, если есть место
            while (len(self.active_downloads) < self.MAX_CONCURRENT_DOWNLOADS and 
                   self.download_queue):
                url, format_id = self.download_queue.pop(0)
                if url not in self.active_downloads:
                    self.start_single_download(url, format_id)
                    # Добавляем небольшую задержку между запусками
                    QThread.msleep(500)
        except Exception as e:
            logger.error(f"Ошибка при обработке очереди: {str(e)}")
            logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
    
    def start_single_download(self, url, format_id):
        try:
            # Находим строку с этим URL
            for row in range(self.url_table.rowCount()):
                if self.url_table.item(row, 0).text() == url:
                    progress_bar = self.url_table.cellWidget(row, 2)
                    if isinstance(progress_bar, QProgressBar):
                        progress_bar.setValue(0)
                        progress_bar.setFormat('Подготовка...')
                        progress_bar.setStyleSheet("""
                            QProgressBar {
                                border: 1px solid #ccc;
                                border-radius: 3px;
                                text-align: center;
                            }
                            QProgressBar::chunk {
                                background-color: #4CAF50;
                                border-radius: 2px;
                            }
                        """)
                        # Принудительно обновляем виджет
                        progress_bar.repaint()
                    break

            worker = DownloadWorker(url, format_id)
            worker.finished.connect(self.download_complete)
            worker.progress.connect(lambda msg, percent: self.update_download_progress(url, msg, percent))
            
            # Добавляем в активные загрузки до запуска
            self.active_downloads[url] = worker
            worker.start()
            
            logger.info(f"Начало скачивания: {url} в формате {format_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке скачивания: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось начать скачивание:\n{str(e)}")

    def update_download_progress(self, url, message, percent):
        """Обновление прогресса конкретной загрузки"""
        try:
            # Добавляем сообщение в лог
            self.log_text.append(message)
            
            # Обновляем прогресс-бар для соответствующего URL
            if percent >= 0:
                for row in range(self.url_table.rowCount()):
                    if self.url_table.item(row, 0).text() == url:
                        progress_bar = self.url_table.cellWidget(row, 2)
                        if isinstance(progress_bar, QProgressBar):
                            # Устанавливаем значение прогресса
                            progress_bar.setValue(int(percent))
                            
                            # Обновляем текст
                            if percent == 0:
                                progress_bar.setFormat('Подготовка...')
                            elif percent == 100:
                                progress_bar.setFormat('Завершено')
                                progress_bar.setStyleSheet("""
                                    QProgressBar {
                                        border: 1px solid #ccc;
                                        border-radius: 3px;
                                        text-align: center;
                                    }
                                    QProgressBar::chunk {
                                        background-color: #45a049;
                                        border-radius: 2px;
                                    }
                                """)
                            else:
                                progress_bar.setFormat(f'Загрузка: {int(percent)}%')
                            
                            # Принудительно обновляем виджет
                            progress_bar.repaint()
                            QApplication.processEvents()  # Обрабатываем события приложения
                        break
                    
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресса: {str(e)}")
            logger.debug(f"Сообщение: {message}, Процент: {percent}")

    def download_complete(self, success, result, thumbnail_path, url):
        try:
            if url in self.active_downloads:
                worker = self.active_downloads[url]
                del self.active_downloads[url]
                worker.quit()
                worker.wait()
            
            for row in range(self.url_table.rowCount()):
                if self.url_table.item(row, 0).text() == url:
                    self.url_table.removeRow(row)
                    break
            
            if success:
                thumb_info = f"\nПревью: {thumbnail_path}" if thumbnail_path else ""
                logger.info(f"Успешно скачано: {url} -> {result}{thumb_info}")
                # Обновляем историю после успешной загрузки
                self.refresh_history()
            else:
                logger.error(f"Ошибка при скачивании {url}: {result}")
            
            # Проверяем, есть ли еще загрузки в очереди
            self.process_queue()
            
            # Если все загрузки завершены
            if not self.active_downloads and not self.download_queue:
                self.download_button.setEnabled(self.url_table.rowCount() > 0)
                self.add_button.setEnabled(True)
                
                if success:
                    QMessageBox.information(self, "Успех", "Все видео успешно скачаны!")
            
        except Exception as e:
            logger.error(f"Ошибка в download_complete: {str(e)}")

    def on_url_changed(self):
        """Обработчик изменения URL"""
        url = self.url_input.text().strip()
        if url:
            try:
                info = get_video_info(url)
                self.info_widget.update_info(info)
            except Exception as e:
                self.info_widget.hide()
                logger.debug(f"Ошибка при получении информации о видео: {str(e)}")

    def download_thumbnail(self):
        """Скачивание только превью"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.critical(self, "Ошибка", "Введите ссылку на видео")
            return
            
        self.thumb_button.setEnabled(False)
        worker = ThumbnailDownloadWorker(url)
        worker.finished.connect(self.thumbnail_download_complete)
        worker.start()
        logger.info(f"Начало скачивания превью: {url}")
        
    def thumbnail_download_complete(self, success, result, url):
        self.thumb_button.setEnabled(True)
        
        if success:
            logger.info(f"Превью успешно скачано: {result}")
            QMessageBox.information(self, "Успех", f"Превью сохранено:\n{result}")
        else:
            logger.error(f"Ошибка при скачивании превью: {result}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось скачать превью:\n{result}")

    def setup_logging(self):
        """Настройка логирования"""
        handler = LogHandler(self.log_text)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)

    def show_video_details(self, item):
        url = item.text()
        try:
            video_info = get_video_info(url)
            dialog = VideoDetailsDialog(video_info, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить информацию о видео:\n{str(e)}")

    def setup_history_tab(self):
        """Настройка вкладки истории"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Таблица истории
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            "Название", "Дата загрузки", "Путь", "Действия"
        ])
        
        # Настройка колонок
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(1, 150)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(3, 100)
        
        layout.addWidget(self.history_table)
        
        # Кнопка обновления
        refresh_button = QPushButton("Обновить историю")
        refresh_button.clicked.connect(self.refresh_history)
        layout.addWidget(refresh_button)
        
        # Загружаем историю при создании вкладки
        self.refresh_history()
        
        return widget

    def refresh_history(self):
        """Обновление списка скачанных видео"""
        try:
            downloaded_videos = db.get_downloaded_videos()
            self.history_table.setRowCount(len(downloaded_videos))
            
            for row, (video_id, url, title, path, date) in enumerate(downloaded_videos):
                # Название
                title_item = QTableWidgetItem(title)
                self.history_table.setItem(row, 0, title_item)
                
                # Дата загрузки
                date_item = QTableWidgetItem(date)
                self.history_table.setItem(row, 1, date_item)
                
                # Путь
                path_item = QTableWidgetItem(path)
                path_item.setToolTip(path)
                self.history_table.setItem(row, 2, path_item)
                
                # Кнопки действий
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                # Кнопка открытия папки
                open_folder = QPushButton("📁")
                open_folder.setToolTip("Открыть папку")
                open_folder.clicked.connect(lambda _, p=path: self.open_file_location(p))
                
                # Кнопка информации
                info_button = QPushButton("ℹ️")
                info_button.setToolTip("Информация о видео")
                info_button.clicked.connect(lambda _, u=url: self.show_video_details(u))
                
                actions_layout.addWidget(open_folder)
                actions_layout.addWidget(info_button)
                
                self.history_table.setCellWidget(row, 3, actions_widget)
            
            logger.info("История обновлена")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении истории: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить историю: {str(e)}")

    def open_file_location(self, path):
        """Открытие папки с файлом"""
        try:
            import os
            import platform
            import subprocess
            
            if platform.system() == "Windows":
                os.startfile(os.path.dirname(path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", os.path.dirname(path)])
            else:  # Linux
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
            
        except Exception as e:
            logger.error(f"Ошибка при открытии папки: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть папку: {str(e)}")

    def load_urls_from_file(self):
        """Загрузка URL из текстового файла"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите файл со ссылками",
                "",
                "Текстовые файлы (*.txt);;Все файлы (*.*)"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'r', encoding='utf-8') as file:
                urls = []
                for line in file:
                    url = line.strip()
                    if url and 'youtube.com' in url or 'youtu.be' in url:
                        # Проверяем, нет ли уже такого URL в списке
                        if not any(self.url_table.item(i, 0).text() == url 
                                 for i in range(self.url_table.rowCount())):
                            urls.append(url)
                
                if urls:
                    for url in urls:
                        self.add_url_to_queue(url)
                    self.download_button.setEnabled(True)
                    logger.info(f"Загружено {len(urls)} ссылок из файла")
                    QMessageBox.information(
                        self,
                        "Успех",
                        f"Загружено {len(urls)} ссылок из файла"
                    )
                else:
                    logger.warning("В файле не найдено новых ссылок на YouTube")
                    QMessageBox.warning(
                        self,
                        "Внимание",
                        "В файле не найдено новых ссылок на YouTube"
                    )
                    
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {str(e)}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось загрузить файл:\n{str(e)}"
            )
    
    def save_urls_to_file(self):
        """Сохранение URL в текстовый файл"""
        try:
            if self.url_table.rowCount() == 0:
                QMessageBox.warning(
                    self,
                    "Внимание",
                    "Список ссылок пуст"
                )
                return
                
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ссылки в файл",
                "",
                "Текстовые файлы (*.txt);;Все файлы (*.*)"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'w', encoding='utf-8') as file:
                for row in range(self.url_table.rowCount()):
                    url = self.url_table.item(row, 0).text()
                    file.write(f"{url}\n")
                    
            logger.info(f"Сохранено {self.url_table.rowCount()} ссылок в файл")
            QMessageBox.information(
                self,
                "Успех",
                f"Сохранено {self.url_table.rowCount()} ссылок в файл"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла: {str(e)}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить файл:\n{str(e)}"
            )

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        try:
            # Проверяем, есть ли активные загрузки
            if self.active_downloads:
                reply = QMessageBox.question(
                    self,
                    'Подтверждение',
                    'Есть активные загрузки. Вы уверены, что хотите выйти?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    event.ignore()
                    return
            
            # Останавливаем все активные потоки
            for worker in self.active_downloads.values():
                worker.quit()
                worker.wait()  # Ждем завершения потока
            
            # Очищаем очередь
            self.download_queue.clear()
            
            # Удаляем обработчики логов
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            
            event.accept()
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии приложения: {str(e)}")
            event.accept()

class ChannelTab(QWidget):
    video_selected = pyqtSignal(str)  # Сигнал для передачи URL в основную вкладку
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Панель ввода
        input_layout = QHBoxLayout()
        
        # Поле для URL канала
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Введите URL канала YouTube")
        input_layout.addWidget(self.channel_input)
        
        # Количество видео
        self.videos_count = QLineEdit()
        self.videos_count.setPlaceholderText("50")
        self.videos_count.setMaximumWidth(100)
        input_layout.addWidget(QLabel("Макс. видео:"))
        input_layout.addWidget(self.videos_count)
        
        # Кнопка загрузки
        self.load_button = QPushButton("Загрузить видео")
        self.load_button.clicked.connect(self.load_channel_videos)
        input_layout.addWidget(self.load_button)
        
        layout.addLayout(input_layout)
        
        # Таблица видео
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(7)
        self.videos_table.setHorizontalHeaderLabels([
            "Выбрать", "Превью", "Название", "Просмотры", 
            "Длительность", "Дата", "Действия"
        ])
        
        # Настройка колонок
        self.videos_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.videos_table.setColumnWidth(0, 70)
        self.videos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.videos_table.setColumnWidth(1, 160)
        self.videos_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.videos_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.videos_table.setColumnWidth(3, 100)
        self.videos_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.videos_table.setColumnWidth(4, 100)
        self.videos_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.videos_table.setColumnWidth(5, 100)
        self.videos_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.videos_table.setColumnWidth(6, 100)
        
        # Устанавливаем высоту строк
        self.videos_table.verticalHeader().setDefaultSectionSize(90)
        
        layout.addWidget(self.videos_table)
        
        # Кнопки действий
        buttons_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("Выбрать все")
        self.select_all_button.clicked.connect(self.select_all_videos)
        buttons_layout.addWidget(self.select_all_button)
        
        self.deselect_all_button = QPushButton("Снять выбор")
        self.deselect_all_button.clicked.connect(self.deselect_all_videos)
        buttons_layout.addWidget(self.deselect_all_button)
        
        self.add_selected_button = QPushButton("Добавить выбранные")
        self.add_selected_button.clicked.connect(self.add_selected_to_queue)
        buttons_layout.addWidget(self.add_selected_button)
        
        layout.addLayout(buttons_layout)
        
        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Настройка логирования
        self.setup_logging()
    
    def setup_logging(self):
        self.log_handler = LogHandler(self.log_text)
        self.log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(self.log_handler)
    
    def load_channel_videos(self):
        channel_url = self.channel_input.text().strip()
        if not channel_url:
            QMessageBox.warning(self, "Внимание", "Введите URL канала")
            return
        
        try:
            max_videos = int(self.videos_count.text() or "50")
            if max_videos <= 0:
                raise ValueError("Количество видео должно быть положительным")
        except ValueError as e:
            QMessageBox.warning(self, "Внимание", str(e))
            return
        
        self.load_button.setEnabled(False)
        self.load_button.setText("Загрузка...")
        QApplication.processEvents()
        
        try:
            videos = get_channel_videos(channel_url, max_videos)
            self.display_videos(videos)
        except Exception as e:
            logger.error(f"Ошибка при загрузке видео: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить видео: {str(e)}")
        finally:
            self.load_button.setEnabled(True)
            self.load_button.setText("Загрузить видео")
    
    def display_videos(self, videos):
        self.videos_table.setRowCount(len(videos))
        
        for row, video in enumerate(videos):
            # Чекбокс
            checkbox = QCheckBox()
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.videos_table.setCellWidget(row, 0, checkbox_widget)
            
            # Превью
            thumbnail_label = self.create_thumbnail_label(video.get('thumbnail'))
            self.videos_table.setCellWidget(row, 1, thumbnail_label)
            
            # Название
            title_item = QTableWidgetItem(video['title'])
            title_item.setToolTip(video['title'])
            self.videos_table.setItem(row, 2, title_item)
            
            # Просмотры
            views = QTableWidgetItem(f"{video['views']:,}".replace(',', ' '))
            views.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.videos_table.setItem(row, 3, views)
            
            # Длительность
            duration = str(timedelta(seconds=video['duration'])).split('.')[0]
            duration_item = QTableWidgetItem(duration)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.videos_table.setItem(row, 4, duration_item)
            
            # Дата загрузки
            upload_date = video.get('upload_date', '')
            if upload_date:
                try:
                    date = datetime.strptime(upload_date, '%Y%m%d')
                    date_str = date.strftime('%d.%m.%Y')
                except:
                    date_str = upload_date
            else:
                date_str = 'Неизвестно'
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.videos_table.setItem(row, 5, date_item)
            
            # Кнопки действий
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            info_button = QPushButton("ℹ️")
            info_button.setToolTip("Информация")
            info_button.clicked.connect(lambda _, u=video['url']: self.show_video_details(u))
            
            add_button = QPushButton("➕")
            add_button.setToolTip("Добавить в очередь")
            # Сохраняем URL как свойство кнопки
            add_button._url = video['url']
            add_button.clicked.connect(lambda _, u=video['url']: self.video_selected.emit(u))
            
            actions_layout.addWidget(info_button)
            actions_layout.addWidget(add_button)
            
            self.videos_table.setCellWidget(row, 6, actions_widget)
    
    def select_all_videos(self):
        self.set_all_checkboxes(True)
    
    def deselect_all_videos(self):
        self.set_all_checkboxes(False)
    
    def set_all_checkboxes(self, checked):
        for row in range(self.videos_table.rowCount()):
            checkbox_widget = self.videos_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(checked)
    
    def add_selected_to_queue(self):
        selected_videos = []
        for row in range(self.videos_table.rowCount()):
            checkbox_widget = self.videos_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    title = self.videos_table.item(row, 2).text()
                    # Получаем URL из кнопки добавления
                    actions_widget = self.videos_table.cellWidget(row, 6)
                    for button in actions_widget.findChildren(QPushButton):
                        if button.toolTip() == "Добавить в очередь":
                            url = button._url  # Просто получаем URL из свойства кнопки
                            selected_videos.append((title, url))
                            self.video_selected.emit(url)
                            break
        
        if selected_videos:
            logger.info(f"Добавлено {len(selected_videos)} видео в очередь: {[title for title, _ in selected_videos]}")
        else:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одного видео")
    
    def create_thumbnail_label(self, thumbnail_url):
        """Создание виджета для превью"""
        label = QLabel()
        label.setFixedSize(160, 90)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background-color: #f0f0f0; border-radius: 4px;")
        
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url)
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                label.setPixmap(pixmap)
            except:
                label.setText("Нет превью")
        else:
            label.setText("Нет превью")
            
        return label
    
    def show_video_details(self, url):
        try:
            video_info = get_video_info(url)
            dialog = VideoDetailsDialog(video_info, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить информацию о видео:\n{str(e)}")

def main():
    try:
        app = QApplication(sys.argv)
        window = VideoDownloaderApp()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        logger.error(f"Критическая ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 