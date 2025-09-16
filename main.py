# main.py
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from main_window import MainWindow
from util import resource_path

if __name__ == "__main__":
    # On Windows, set an explicit AppUserModelID so the taskbar uses our icon
    if sys.platform.startswith("win"):
        try:
            import ctypes  # noqa: F401
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BAR.Keybinder")
        except Exception:
            pass

    app = QApplication(sys.argv)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = None
    for rel in ("assets/icon.ico", "icon.ico", "assets/icon.png", "icon.png"):
        p = resource_path(rel)
        if os.path.exists(p):
            icon_path = p
            break
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    
    # Apply a modern style if available
    try:
        import qdarktheme
        app.setStyleSheet(qdarktheme.load_stylesheet())
    except ImportError:
        print("qdarktheme not found. Using default style. Install with: pip install pyqtdarktheme")

    window = MainWindow()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))
    window.show()
    sys.exit(app.exec())