from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QFrame,
    QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
try:
    from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    # Заглушки для графиков
    class QChart:
        class ChartTheme:
            ChartThemeDark = 0
        class AnimationOption:
            AllAnimations = 0
            
        def setTheme(self, *args): pass
        def setAnimationOptions(self, *args): pass
        def addSeries(self, *args): pass
        def addAxis(self, *args, **kwargs): pass
        def legend(self): return ChartLegend()
        
    class ChartLegend:
        def setVisible(self, *args): pass
        def setAlignment(self, *args): pass
    
    class QChartView(QFrame):
        def __init__(self, chart=None, parent=None):
            super().__init__(parent)
            self.setMinimumHeight(300)
            self.setStyleSheet("""
                QFrame {
                    background-color: #363636;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            layout = QVBoxLayout(self)
            label = QLabel("Для отображения графиков установите PyQt6-Charts:\npip install PyQt6-Charts")
            label.setStyleSheet("color: white;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            
        def setRenderHint(self, *args): pass
    
    class QLineSeries:
        def setName(self, *args): pass
        def clear(self): pass
        def append(self, *args): pass
        def attachAxis(self, *args): pass
    
    class QValueAxis:
        def setRange(self, *args): pass
        def setTickCount(self, *args): pass
        def setLabelFormat(self, *args): pass
    
    class QDateTimeAxis:
        def setFormat(self, *args): pass
        def setRange(self, *args): pass
        def setTickCount(self, *args): pass

from PyQt6.QtGui import QPainter
from core.vk_api import VkApi
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StatsWidget(QWidget):
    def __init__(self, title, value, change=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #363636;
                border-radius: 8px;
            }
            QLabel {
                color: white;
            }
        """)
        
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(5)  # Уменьшаем отступы между элементами
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #888;")
        frame_layout.addWidget(title_label)
        
        # Значение
        value_label = QLabel(str(value))
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        frame_layout.addWidget(value_label)
        
        # Изменение
        if change is not None:
            change_label = QLabel(f"{'+' if change >= 0 else ''}{change}%")
            change_label.setStyleSheet(
                f"color: {'#28a745' if change >= 0 else '#dc3545'}; "
                "font-size: 12px;"
            )
            frame_layout.addWidget(change_label)
            
        layout.addWidget(frame)

class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vk_api = VkApi()
        self.init_ui()
        
        # Обновление каждые 5 минут
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(300000)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)  # Добавляем отступы между элементами
        
        # Верхняя панель
        top_panel = QHBoxLayout()
        
        # Период
        period_label = QLabel("Период:")
        period_label.setStyleSheet("color: white;")
        top_panel.addWidget(period_label)
        
        self.period_combo = QComboBox()
        self.period_combo.setStyleSheet("""
            QComboBox {
                background-color: #363636;
                color: white;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
                min-width: 150px;
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
        """)
        self.period_combo.addItems([
            "За сегодня",
            "За неделю",
            "За месяц",
            "За все время"
        ])
        self.period_combo.currentIndexChanged.connect(self.update_stats)
        top_panel.addWidget(self.period_combo)
        
        # Обновить
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.update_stats)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        top_panel.addWidget(refresh_btn)
        
        top_panel.addStretch()
        layout.addLayout(top_panel)
        
        # Область прокрутки для статистики
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #2b2b2b;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        scroll_content = QWidget()
        self.stats_layout = QGridLayout(scroll_content)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(20)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # График
        self.chart_view = self.create_chart()
        layout.addWidget(self.chart_view)
        
        # Загружаем начальную статистику
        self.update_stats()
        
    def create_chart(self):
        chart = QChart()
        if CHARTS_AVAILABLE:
            chart.setTheme(QChart.ChartTheme.ChartThemeDark)
            chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        
        # Создаем серии данных
        self.views_series = QLineSeries()
        self.views_series.setName("Просмотры")
        
        self.likes_series = QLineSeries()
        self.likes_series.setName("Лайки")
        
        chart.addSeries(self.views_series)
        chart.addSeries(self.likes_series)
        
        # Оси
        axis_x = QDateTimeAxis()
        axis_x.setFormat("dd.MM")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.views_series.attachAxis(axis_x)
        self.likes_series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        self.views_series.attachAxis(axis_y)
        self.likes_series.attachAxis(axis_y)
        
        # Настройки отображения
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        view = QChartView(chart)
        if CHARTS_AVAILABLE:
            view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        return view
        
    def update_stats(self):
        try:
            access_token = self.vk_api.get_current_token()
            if not access_token:
                raise ValueError("Требуется авторизация VK")
                
            # Получаем статистику
            videos = self.vk_api.get_videos(access_token)
            
            total_views = sum(video.get('views', 0) for video in videos)
            total_likes = sum(video.get('likes', 0) for video in videos)
            total_comments = sum(video.get('comments', 0) for video in videos)
            
            # Очищаем старую статистику
            for i in reversed(range(self.stats_layout.count())): 
                self.stats_layout.itemAt(i).widget().setParent(None)
            
            # Добавляем виджеты статистики
            self.stats_layout.addWidget(StatsWidget("Всего видео", len(videos)), 0, 0)
            self.stats_layout.addWidget(StatsWidget("Просмотры", total_views, 5), 0, 1)
            self.stats_layout.addWidget(StatsWidget("Лайки", total_likes, -2), 0, 2)
            self.stats_layout.addWidget(StatsWidget("Комментарии", total_comments, 3), 0, 3)
            
            # Обновляем график
            self.update_chart(videos)
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {str(e)}")
            
    def update_chart(self, videos):
        # Очищаем старые данные
        self.views_series.clear()
        self.likes_series.clear()
        
        # Сортируем видео по дате
        videos.sort(key=lambda x: datetime.strptime(x['date'], '%d.%m.%Y'))
        
        # Добавляем точки на график
        for video in videos:
            date = datetime.strptime(video['date'], '%d.%m.%Y')
            timestamp = date.timestamp() * 1000  # Qt использует миллисекунды
            
            self.views_series.append(timestamp, video.get('views', 0))
            self.likes_series.append(timestamp, video.get('likes', 0))

    def refresh_stats(self):
        """Обновление статистики"""
        try:
            # Обновляем статистику
            self.load_stats()
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {str(e)}") 