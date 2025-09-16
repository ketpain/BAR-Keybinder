# main_window.py
import os
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QComboBox, QTableView, QHeaderView, QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import QSortFilterProxyModel, Qt, QModelIndex

from model import KeybindTableModel
from delegates import ButtonDelegate
from key_capture import KeyCaptureDialog

class KeybindSortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._show_unbound_only = False
        self._show_changed_only = False

    def set_filters(self, show_unbound, show_changed):
        self._show_unbound_only = show_unbound
        self._show_changed_only = show_changed
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        keybind = model.data(index, Qt.ItemDataRole.UserRole)

        if self._show_unbound_only and keybind.is_bound:
            return False
        if self._show_changed_only and not keybind.is_changed:
            return False
        
        return True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BAR Keybind Editor (PyQt6 Version)")
        self.setGeometry(100, 100, 1280, 1024)

        # --- File Paths ---
        self.filename = r"C:\\Program Files\\Beyond-All-Reason\\data\\uikeys.txt"
        self.defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default keys.txt")

        # --- UI Setup ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top control bar
        top_bar_layout = QHBoxLayout()
        self.file_label = QLabel(f"Editing: {self.filename}")
        self.load_button = QPushButton("Load / Reload")
        self.save_button = QPushButton("Save Changes")
        self.unbound_check = QCheckBox("Show unbound only")
        self.changed_check = QCheckBox("Show changed only")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Original", "Action A→Z", "Unbound first"])

        top_bar_layout.addWidget(self.file_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.sort_combo)
        top_bar_layout.addWidget(self.unbound_check)
        top_bar_layout.addWidget(self.changed_check)
        top_bar_layout.addWidget(self.load_button)
        top_bar_layout.addWidget(self.save_button)
        main_layout.addLayout(top_bar_layout)

        # Table View
        self.table_view = QTableView()
        main_layout.addWidget(self.table_view)

        # --- Model and View Connection ---
        self.model = KeybindTableModel()
        self.proxy_model = KeybindSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        # --- Delegates for custom columns ---
        self.button_delegate = ButtonDelegate(self)
        self.table_view.setItemDelegateForColumn(2, self.button_delegate)
        self.table_view.setItemDelegateForColumn(3, self.button_delegate)

        # --- Table View Appearance ---
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)

        # --- Connect Signals and Slots ---
        self.load_button.clicked.connect(self.load_keybinds)
        self.save_button.clicked.connect(self.save_keybinds)
        self.unbound_check.stateChanged.connect(self.apply_filters)
        self.changed_check.stateChanged.connect(self.apply_filters)
        self.sort_combo.currentTextChanged.connect(self.apply_sort)
        self.table_view.doubleClicked.connect(self.on_table_double_clicked)

        # --- Initial Load ---
        self.load_keybinds()

    def load_keybinds(self):
        if not os.path.exists(self.filename):
            path, _ = QFileDialog.getOpenFileName(self, "Select uikeys.txt", self.filename, "Text files (*.txt)")
            if not path:
                QMessageBox.critical(self, "Error", "No keybind file selected. Application cannot proceed.")
                return
            self.filename = path
            self.file_label.setText(f"Editing: {self.filename}")

        try:
            self.model.load_from_file(self.filename, self.defaults_path)
            self.apply_sort(self.sort_combo.currentText()) # Apply initial sort
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load file: {e}")

    def save_keybinds(self):
        try:
            self.model.save_to_file(self.filename)
            QMessageBox.information(self, "Success", f"Keybinds saved to {self.filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file: {e}")

    def apply_filters(self):
        self.proxy_model.set_filters(
            self.unbound_check.isChecked(),
            self.changed_check.isChecked()
        )

    def apply_sort(self, sort_mode):
        self.proxy_model.sort(-1) # Disable default sorting before applying custom
        if sort_mode == "Original":
            # This is tricky. We sort by the original ID stored in the Keybind object.
            # A more robust proxy model would handle this. For now, we reload.
            self.model.load_from_file(self.filename, self.defaults_path)
        elif sort_mode == "Action A→Z":
            self.table_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        elif sort_mode == "Unbound first":
            # Custom sorting is best done in the proxy model's `lessThan` method.
            # For simplicity here, we'll just sort the base model and reset.
            self.model.beginResetModel()
            self.model._keybinds.sort(key=lambda kb: (not kb.is_bound, kb.action.lower()), reverse=True)
            self.model.endResetModel()

    def on_table_double_clicked(self, proxy_index: QModelIndex):
        if proxy_index.column() == 1: # Key column
            capture_dialog = KeyCaptureDialog(self)
            capture_dialog.key_sequence_captured.connect(
                lambda seq: self.update_keybind(proxy_index, seq)
            )
            capture_dialog.exec()

    def update_keybind(self, proxy_index, new_sequence_str):
        source_index = self.proxy_model.mapToSource(proxy_index)
        # The key sequence from the dialog is already a string.
        self.model.setData(source_index, new_sequence_str, Qt.ItemDataRole.EditRole)