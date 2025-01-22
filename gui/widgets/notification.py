from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor

class NotificationWidget(QFrame):
    def __init__(self, text, type='info', parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        colors = {
            'info': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FFC107',
            'error': '#F44336'
        }
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {colors.get(type, colors['info'])};
                border-radius: 5px;
                padding: 10px;
            }}
            QLabel {{
                color: white;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel(text))
        
        # Анимация появления
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Автоматическое скрытие
        QTimer.singleShot(3000, self.hide_animation)
        
    def show_animation(self):
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()
        
    def hide_animation(self):
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.close)
        self.animation.start() 