# delegates.py
from PyQt6.QtWidgets import QStyledItemDelegate, QApplication, QStyle, QStyleOptionButton
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QMouseEvent

class ButtonDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if not index.isValid():
            return

        # We create a temporary button to leverage its drawing capabilities
        from PyQt6.QtWidgets import QPushButton
        button = QPushButton()
        button.setText(index.data(Qt.ItemDataRole.DisplayRole))
        button.setGeometry(option.rect)

        # Determine if the button should be enabled
        keybind = index.data(Qt.ItemDataRole.UserRole)
        model = index.model()
        is_enabled = False
        
        # Column 2 is "Unbind"
        if index.column() == 2:
            is_enabled = keybind.is_bound
        # Column 3 is "Reset"
        elif index.column() == 3:
            default_key = model.sourceModel().get_default_key(keybind.action)
            is_enabled = keybind.is_changed or (default_key and keybind.key.lower() != default_key.lower())

        button.setEnabled(is_enabled)

        # Draw the button onto the cell's painter
        button_option = QStyleOptionButton()
        button_option.rect = option.rect
        button_option.text = button.text()
        button_option.state = QStyle.StateFlag.State_Enabled if button.isEnabled() else QStyle.StateFlag.State_None
        
        # Check if the mouse is over the button
        if option.state & QStyle.StateFlag.State_MouseOver:
            button_option.state |= QStyle.StateFlag.State_MouseOver

        style = QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_PushButton, button_option, painter, button)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if option.rect.contains(event.pos()):
                source_model = model.sourceModel()
                source_index = model.mapToSource(index)
                
                if index.column() == 2: # Unbind
                    source_model.unbind_keybind(source_index.row())
                elif index.column() == 3: # Reset
                    source_model.reset_keybind(source_index.row())
                
                return True
        return super().editorEvent(event, model, option, index)