# model.py
import os
from dataclasses import dataclass, field
from collections import defaultdict
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex

# A clean data structure for a single keybind
@dataclass
class Keybind:
    id: int
    action: str
    key: str
    original_key: str | None
    is_synthetic: bool = False

    @property
    def is_bound(self) -> bool:
        return self.key.lower().strip() not in ("", "unbound")

    @property
    def is_changed(self) -> bool:
        if self.is_synthetic:
            return self.is_bound
        return self.key.lower().strip() != (self.original_key or "").lower().strip()

# The model that interfaces with Qt's Model/View framework
class KeybindTableModel(QAbstractTableModel):
    HEADERS = ["Action", "Key", "", ""] # Columns for Action, Key, Unbind, Reset

    def __init__(self, parent=None):
        super().__init__(parent)
        self._keybinds: list[Keybind] = []
        self._other_lines: list[str] = [] # For comments, etc.
        self._default_action_to_keys = {}
        self._duplicate_keys = set()

    # --- Required QAbstractTableModel methods ---

    def rowCount(self, parent=QModelIndex()):
        return len(self._keybinds)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        keybind = self._keybinds[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return keybind.action
            if col == 1:
                return keybind.key
            if col == 2:
                return "Unbind"
            if col == 3:
                return "Reset"
        
        elif role == Qt.ItemDataRole.UserRole: # Return the whole object for delegates
            return keybind
            
        elif role == Qt.ItemDataRole.ToolTipRole and col == 1:
            if keybind.is_synthetic:
                return f"Default: {self.get_default_key(keybind.action) or 'None'}"
            return f"Original: {keybind.original_key or 'None'}"

        elif role == Qt.ItemDataRole.BackgroundRole:
            if keybind.is_bound and keybind.key.lower() in self._duplicate_keys:
                from PyQt6.QtGui import QColor
                return QColor("#602020")

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole and index.column() == 1:
            row = index.row()
            if 0 <= row < len(self._keybinds):
                self._keybinds[row].key = value
                self.check_for_duplicates()
                # Emit dataChanged for the whole row to update buttons and duplicate coloring
                self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))
                # Also emit dataChanged for all other rows to update duplicate status
                self.dataChanged.emit(self.index(0, 1), self.index(self.rowCount()-1, 1), [Qt.ItemDataRole.BackgroundRole])
                return True
        return False

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        flags = super().flags(index)
        # Make column 1 (Key) not editable directly.
        # We want to force users to use the KeyCaptureDialog.
        # if index.column() == 1:
        #     flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    # --- Custom Model Logic ---

    def _parse_line(self, line):
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            return {"type": "other", "original": line}
        parts = stripped.split(None, 2)
        if len(parts) > 1 and parts[0] == "bind":
            if len(parts) == 3:
                return {"type": "bind", "key": parts[1], "action": parts[2]}
        return {"type": "other", "original": line}

    def load_from_file(self, filepath: str, defaults_path: str):
        self.beginResetModel()
        self._keybinds.clear()
        self._other_lines.clear()
        self._default_action_to_keys.clear()

        # Load defaults first
        default_actions = set()
        if os.path.exists(defaults_path):
            with open(defaults_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parsed = self._parse_line(line)
                    if parsed.get("type") == "bind":
                        act = parsed.get("action")
                        key = parsed.get("key")
                        if act:
                            default_actions.add(act)
                            if key:
                                self._default_action_to_keys.setdefault(act, []).append(key)
        
        # Load main file
        with open(filepath, "r") as f:
            lines = f.readlines()

        current_actions = set()
        for i, line in enumerate(lines):
            parsed = self._parse_line(line)
            if parsed.get("type") == "bind":
                action = parsed["action"]
                key = parsed["key"]
                self._keybinds.append(Keybind(id=i, action=action, key=key, original_key=key))
                current_actions.add(action)
            else:
                self._other_lines.append(parsed["original"])

        # Add missing actions from defaults
        missing_actions = sorted(list(default_actions - current_actions))
        next_id = len(lines)
        for action in missing_actions:
            self._keybinds.append(Keybind(
                id=next_id, action=action, key="unbound", original_key=None, is_synthetic=True
            ))
            next_id += 1
        
        self.check_for_duplicates()
        self.endResetModel()

    def save_to_file(self, filepath: str):
        with open(filepath, "w") as f:
            f.write("unbindall\n")
            for line in self._other_lines:
                if not line.strip().lower().startswith("unbindall"):
                    f.write(line)
            
            for kb in self._keybinds:
                if kb.is_bound:
                    f.write(f"bind          {kb.key:<15}  {kb.action}\n")

    def check_for_duplicates(self):
        key_counts = defaultdict(int)
        for kb in self._keybinds:
            if kb.is_bound:
                key_counts[kb.key.lower()] += 1
        
        self._duplicate_keys = {key for key, count in key_counts.items() if count > 1}

    def get_default_key(self, action: str) -> str | None:
        keys = self._default_action_to_keys.get(action)
        return keys[0] if keys else None

    def unbind_keybind(self, row: int):
        if 0 <= row < len(self._keybinds):
            self._keybinds[row].key = "unbound"
            self.check_for_duplicates()
            # Emit dataChanged for the whole row to update all columns
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def reset_keybind(self, row: int):
        if 0 <= row < len(self._keybinds):
            keybind = self._keybinds[row]
            
            reset_key = keybind.original_key
            if keybind.is_synthetic or reset_key is None:
                reset_key = self.get_default_key(keybind.action)

            keybind.key = reset_key or "unbound"
            self.check_for_duplicates()
            # Emit dataChanged for the whole row
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))