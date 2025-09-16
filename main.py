# main.py
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply a modern style if available
    try:
        import qdarktheme
        app.setStyleSheet(qdarktheme.load_stylesheet())
    except ImportError:
        print("qdarktheme not found. Using default style. Install with: pip install pyqtdarktheme")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())