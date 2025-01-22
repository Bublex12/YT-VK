LIGHT_THEME = """
QMainWindow {
    background-color: #f0f0f0;
}

QLabel {
    color: #333;
}

QPushButton {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 5px 15px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #0056b3;
}

QLineEdit {
    padding: 5px;
    border: 1px solid #ccc;
    border-radius: 3px;
}

QProgressBar {
    border: 1px solid #ccc;
    border-radius: 3px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #007bff;
}

QListWidget {
    border: 1px solid #ccc;
    border-radius: 3px;
}
"""

DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
}

QLabel {
    color: #fff;
}

QPushButton {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 5px 15px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #0056b3;
}

QLineEdit {
    padding: 5px;
    border: 1px solid #333;
    border-radius: 3px;
    background-color: #2b2b2b;
    color: white;
}

QProgressBar {
    border: 1px solid #333;
    border-radius: 3px;
    text-align: center;
    color: white;
    background-color: #2b2b2b;
}

QProgressBar::chunk {
    background-color: #007bff;
}

QListWidget {
    border: 1px solid #333;
    border-radius: 3px;
    background-color: #2b2b2b;
    color: white;
}
"""

# Стили для всплывающих окон
DIALOG_STYLE = """
QMessageBox {
    background-color: #2b2b2b;
}
QMessageBox QLabel {
    color: white;
    font-size: 12px;
}
QMessageBox QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 5px 15px;
    border-radius: 3px;
    min-width: 80px;
}
QMessageBox QPushButton:hover {
    background-color: #45a049;
}
QMessageBox QPushButton:pressed {
    background-color: #3d8b40;
}
"""

# Стили для информационных сообщений
INFO_DIALOG_STYLE = DIALOG_STYLE + """
QMessageBox {
    border: 2px solid #4CAF50;
}
QMessageBox QLabel {
    color: #4CAF50;
}
"""

# Стили для предупреждений
WARNING_DIALOG_STYLE = DIALOG_STYLE + """
QMessageBox {
    border: 2px solid #ffc107;
}
QMessageBox QLabel {
    color: #ffc107;
}
"""

# Стили для ошибок
ERROR_DIALOG_STYLE = DIALOG_STYLE + """
QMessageBox {
    border: 2px solid #dc3545;
}
QMessageBox QLabel {
    color: #dc3545;
}
""" 