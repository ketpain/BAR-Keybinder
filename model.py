# model.py
import os
from dataclasses import dataclass, field
from collections import defaultdict
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex

# A clean data structure for a single keybind
def _normalize_token(tok: str) -> str:
    t = tok.strip().lower()
    if t in ("any",):
        return "any"
    if t in ("control", "ctl", "ctrl"): t = "ctrl"
    elif t in ("option", "alt"): t = "alt"
    elif t in ("shift",): t = "shift"
    elif t in ("super", "win", "meta", "cmd"): t = "meta"
    elif t in ("escape",): t = "esc"
    elif t in ("return",): t = "enter"
    elif t in ("del",): t = "delete"
    elif t in ("pgup",): t = "pageup"
    elif t in ("pgdn",): t = "pagedown"

    if len(t) >= 2 and t[0] == 'f' and t[1:].isdigit():
        return t
    if len(t) == 1 and t.isalpha():
        return f"sc_{t}"
    return t

def _normalize_combo(combo: str) -> str:
    parts = [p for p in combo.split('+') if p.strip()]
    if not parts:
        return ""

    mods: list[str] = []
    keys: list[str] = []
    other_mods: list[str] = []
    saw_any = False
    for p in parts:
        nt = _normalize_token(p)
        if nt == "any":
            saw_any = True
        elif nt in ("ctrl", "alt", "shift", "meta"):
            if nt not in other_mods:
                other_mods.append(nt)
        else:
            keys.append(nt)

    if saw_any:
        # In Any-mode, ignore all extra modifiers for matching purposes
        mods = ["any"]
        # If no explicit key provided, allow a single modifier as the key (e.g., Any+shift)
        if not keys and other_mods:
            keys = [other_mods[0]]
    else:
        mods = other_mods[:]

    order = {"any": -1, "ctrl": 0, "alt": 1, "shift": 2, "meta": 3}
    mods.sort(key=lambda m: order[m])

    left = "+".join(mods)
    right = "+".join(keys) if keys else ""
    if left and right:
        return f"{left}+{right}"
    return left or right

def normalize_key(key: str | None) -> str:
    if not key:
        return ""
    seq = [_normalize_combo(k.strip()) for k in key.split(',') if k.strip()]
    return ",".join(seq)
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
        curr = normalize_key(self.key)
        orig = normalize_key(self.original_key)
        return curr != orig

# The model that interfaces with Qt's Model/View framework
class KeybindTableModel(QAbstractTableModel):
    HEADERS = ["Action", "Key", "", ""] # Columns for Action, Key, Unbind, Reset

    def __init__(self, parent=None):
        super().__init__(parent)
        self._keybinds: list[Keybind] = []
        self._other_lines: list[str] = [] # For comments, etc.
        self._default_action_to_keys: dict[str, list[str]] = {}
        self._duplicate_keys = set()
        # Normalization helpers moved to module level

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
            default_key = self.get_default_key(keybind.action)
            parts = []
            parts.append("Double-click to change")
            parts.append(f"Default: {default_key or 'None'}")
            parts.append(f"Original: {keybind.original_key or 'None'}")
            return " | ".join(parts)

        elif role == Qt.ItemDataRole.BackgroundRole:
            if keybind.is_bound and normalize_key(keybind.key) in self._duplicate_keys:
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
        if role == Qt.ItemDataRole.ToolTipRole and orientation == Qt.Orientation.Horizontal:
            if section == 1:
                return "Double-click a Key cell to set a new key"
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

        # Load defaults first (robust against mispackaged directories)
        default_actions = set()
        if defaults_path:
            candidates: list[str] = []
            if os.path.isfile(defaults_path):
                candidates.append(defaults_path)
            elif os.path.isdir(defaults_path):
                inner = os.path.join(defaults_path, os.path.basename(defaults_path))
                if os.path.isfile(inner):
                    candidates.append(inner)
            if not candidates:
                # Last-resort: look beside the main file
                sibling = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.basename(defaults_path))
                if os.path.isfile(sibling):
                    candidates.append(sibling)

            for path in candidates:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            parsed = self._parse_line(line)
                            if parsed.get("type") == "bind":
                                act = parsed.get("action")
                                key = parsed.get("key")
                                if act:
                                    default_actions.add(act)
                                    if key:
                                        self._default_action_to_keys.setdefault(act, []).append(key)
                    break  # Loaded successfully
                except PermissionError:
                    # Try next candidate
                    continue
        
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
                norm = normalize_key(kb.key)
                if norm:
                    key_counts[norm] += 1
        self._duplicate_keys = {key for key, count in key_counts.items() if count > 1}

    def get_default_key(self, action: str) -> str | None:
        keys = self._default_action_to_keys.get(action)
        return keys[0] if keys else None

    def get_default_keys(self, action: str) -> list[str]:
        return self._default_action_to_keys.get(action, [])

    def is_default_match(self, action: str, key: str | None) -> bool:
        if not key:
            return False
        target = normalize_key(key)
        for k in self.get_default_keys(action):
            if normalize_key(k) == target:
                return True
        return False

    def unbind_keybind(self, row: int):
        if 0 <= row < len(self._keybinds):
            self._keybinds[row].key = "unbound"
            self.check_for_duplicates()
            # Emit dataChanged for the whole row to update all columns
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def reset_keybind(self, row: int):
        if 0 <= row < len(self._keybinds):
            keybind = self._keybinds[row]
            # Prefer true defaults from defaults file; fall back to original.
            defaults = self.get_default_keys(keybind.action)
            chosen = None
            if defaults:
                # Try to pick the default that best matches the original or current (normalized)
                norm_orig = normalize_key(keybind.original_key)
                norm_curr = normalize_key(keybind.key)
                # Exact match to original default
                for d in defaults:
                    if normalize_key(d) == norm_orig and norm_orig:
                        chosen = d
                        break
                if not chosen:
                    for d in defaults:
                        if normalize_key(d) == norm_curr and norm_curr:
                            chosen = d
                            break
                if not chosen:
                    # Fallback to first default
                    chosen = defaults[0]
            else:
                chosen = keybind.original_key

            keybind.key = chosen or "unbound"
            self.check_for_duplicates()
            # Emit dataChanged for the whole row
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))