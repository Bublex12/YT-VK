from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen

class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(False)
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(500)  # Длительность анимации в мс
        
    def setValue(self, value):
        self.animation.stop()
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()

class ProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Прогресс-бар
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #363636;
                height: 4px;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Текст прогресса
        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                min-width: 45px;
                padding-left: 10px;
            }
        """)
        layout.addWidget(self.progress_label)
        
        # Анимация линии загрузки
        self.line_timer = QTimer()
        self.line_timer.timeout.connect(self.update_line_animation)
        self.line_value = 0
        
        # Индикатор загрузки
        self.loading_dots = 0
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_dots)
        
        self.is_indeterminate = False
        
    def set_progress(self, value):
        """Установка значения прогресса"""
        if self.is_indeterminate:
            self.stop_animation()
            
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")
        
    def start_animation(self):
        """Запуск анимации неопределенного прогресса"""
        self.is_indeterminate = True
        self.progress_bar.setMaximum(0)
        self.loading_timer.start(300)  # Обновление точек каждые 300мс
        self.line_timer.start(50)  # Обновление линии каждые 50мс
        
    def stop_animation(self):
        """Остановка анимации"""
        self.is_indeterminate = False
        self.loading_timer.stop()
        self.line_timer.stop()
        self.progress_bar.setMaximum(100)
        
    def update_loading_dots(self):
        """Обновление анимации точек загрузки"""
        self.loading_dots = (self.loading_dots + 1) % 4
        self.progress_label.setText("." * self.loading_dots)
        
    def update_line_animation(self):
        """Обновление анимации линии"""
        self.line_value = (self.line_value + 1) % 100
        self.update()  # Вызываем перерисовку
        
    def paintEvent(self, event):
        """Отрисовка дополнительных эффектов"""
        if self.is_indeterminate:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Рисуем пульсирующую линию
            pen = QPen(QColor("#4CAF50"))
            pen.setWidth(2)
            painter.setPen(pen)
            
            width = self.progress_bar.width()
            pos = (self.line_value * width) % (width * 2)
            if pos > width:
                pos = width * 2 - pos
            
            painter.drawLine(int(pos - 20), 2, int(pos + 20), 2) 