"""
EasyStock — punto de entrada.
Ejecutar: python main.py

Dependencias:
    pip install PyQt6 matplotlib pandas openpyxl
"""
import sys
from PyQt6.QtWidgets import QApplication
from easystock.config import QSS
from easystock.ui import MainApp


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("EasyStock")
    app.setStyleSheet(QSS)

    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
