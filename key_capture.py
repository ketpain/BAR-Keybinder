# key_capture.py
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent

class KeyCaptureDialog(QDialog):
    key_sequence_captured = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Capture Keybind")
        self.setMinimumSize(300, 100)

        self.info_label = QLabel("Press keys… (multi-tap supported)")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.info_label.font()
        font.setPointSize(14)
        self.info_label.setFont(font)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)

        self.sequence_parts = []
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(450) # Multi-tap timeout
        self.timer.timeout.connect(self.finalize_sequence)

    def keyPressEvent(self, event: QKeyEvent):
        key_text = self.format_key_event(event)
        if key_text:
            self.sequence_parts.append(key_text)
            self.info_label.setText(",".join(self.sequence_parts))
            self.timer.start()

    def finalize_sequence(self):
        if self.sequence_parts:
            self.key_sequence_captured.emit(",".join(self.sequence_parts))
        self.accept()

    def format_key_event(self, event: QKeyEvent) -> str | None:
        key = event.key()
        mods = event.modifiers()
        text = event.text()

        # Ignore pure modifier presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return None

        mod_list = []
        if mods & Qt.KeyboardModifier.ControlModifier: mod_list.append("Ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier: mod_list.append("Shift")
        if mods & Qt.KeyboardModifier.AltModifier: mod_list.append("Alt")
        
        prefix = "+".join(mod_list) + ("+" if mod_list else "")

        # Special keys mapping
        key_map = {
            Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Tab: "tab", Qt.Key.Key_Escape: "esc", Qt.Key.Key_Space: "space",
            Qt.Key.Key_Delete: "delete", Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup", Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right",
            Qt.Key.Key_Insert: "insert", Qt.Key.Key_Pause: "pause",
            Qt.Key.Key_F1: "F1", Qt.Key.Key_F2: "F2", Qt.Key.Key_F3: "F3", Qt.Key.Key_F4: "F4",
            Qt.Key.Key_F5: "F5", Qt.Key.Key_F6: "F6", Qt.Key.Key_F7: "F7", Qt.Key.Key_F8: "F8",
            Qt.Key.Key_F9: "F9", Qt.Key.Key_F10: "F10", Qt.Key.Key_F11: "F11", Qt.Key.Key_F12: "F12",
        }
        if key in key_map:
            return f"{prefix}{key_map[key]}"

        # Numpad keys
        if Qt.Key.Key_NumLock < key < Qt.Key.Key_Select:
            # A simple way to handle numpad keys
            return f"{prefix}numpad{text}"

        # Printable characters
        if text and text.isprintable() and text.isalpha():
            return f"{prefix}sc_{text.lower()}"
        if text and text.isprintable():
            return f"{prefix}{text}"

        return None