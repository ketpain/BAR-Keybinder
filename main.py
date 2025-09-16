import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os
import sys
import ctypes

# Set the appearance and color theme for the UI
ctk.set_appearance_mode("System")  # Can be "System", "Dark", "Light"
ctk.set_default_color_theme("blue")

class KeybindEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("BAR Keybind Editor")
        self.geometry("1000x1024")

        # --- Data Storage ---
        # This list will hold our parsed keybind data.
        # Each item will be a dictionary representing one line from the file.
        self.keybind_data = []
        # This dictionary will link a specific keybind's data to its UI entry widget
        self.ui_widgets = {}
        self.filename = r"C:\\Program Files\\Beyond-All-Reason\\data\\uikeys.txt"
        # Optional defaults file bundled next to this script
        self.defaults_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "original keys.txt")

        # --- Runtime State ---
        self.listening_entry = None
        self.active_mods = set()  # tracks currently pressed modifiers while listening
        self.saw_alt_press = False
        self.saw_any_nonmod_key = False
        self.DEBUG = False  # set True to print key event debug info
        self.show_only_unbound = ctk.BooleanVar(value=False)
        self.show_only_changed = ctk.BooleanVar(value=False)
        self.sort_mode = ctk.StringVar(value="Original")
        # Defaults: action -> [keys] from original keys file
        self.default_action_to_keys = {}

        # --- UI Layout ---
        # Configure the grid layout (2 rows, 1 column)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Top Frame for Controls ---
        self.top_frame = ctk.CTkFrame(self, height=50)
        self.top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.file_label = ctk.CTkLabel(self.top_frame, text=f"Editing: {self.filename}")
        self.file_label.pack(side="left", padx=10)

        self.save_button = ctk.CTkButton(self.top_frame, text="Save Changes", command=self.save_keybinds)
        self.save_button.pack(side="right", padx=10)

        self.load_button = ctk.CTkButton(self.top_frame, text="Load / Reload", command=self.load_and_display_keybinds)
        self.load_button.pack(side="right", padx=10)

        self.unbound_only_check = ctk.CTkCheckBox(
            self.top_frame,
            text="Show unbound only",
            variable=self.show_only_unbound,
            command=self.on_toggle_unbound_only,
        )
        self.unbound_only_check.pack(side="right", padx=10)

        self.changed_only_check = ctk.CTkCheckBox(
            self.top_frame,
            text="Show changed only",
            variable=self.show_only_changed,
            command=self.on_toggle_changed_only,
        )
        self.changed_only_check.pack(side="right", padx=10)

        self.sort_menu = ctk.CTkOptionMenu(
            self.top_frame,
            values=["Original", "Unbound first", "Action A→Z"],
            variable=self.sort_mode,
            command=lambda _: self.on_change_sort(),
        )
        self.sort_menu.set("Original")
        self.sort_menu.pack(side="right", padx=10)

        # --- Main Scrollable Frame for Keybinds ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Keybinds")
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Inner content frame to host rows; we control its width to avoid
        # continuous reflow while the window is being resized.
        self.content_frame = ctk.CTkFrame(self.scrollable_frame)
        self.content_frame.pack(anchor="nw")  # width managed explicitly
        self.content_frame.pack_propagate(False)

        # Grid config for rows: column 0 stretches (action), column 1 fixed (entry), columns 2-3 buttons
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0)
        self.content_frame.grid_columnconfigure(2, weight=0)
        self.content_frame.grid_columnconfigure(3, weight=0)

        # Debounced resize handler state
        self._resize_after_id = None
        self.bind("<Configure>", self._on_configure)

        # Initialize content width after first layout
        self.after(0, self._init_content_width)

        # Batched UI build settings/state
        self._build_batch_size = 80
        self._build_ctx = None  # holds: {frame, index, row_index}
        self._build_after_id = None
        # Multi-tap capture state
        self.sequence_parts = None
        self.sequence_after_id = None
        self.sequence_timeout_ms = 450
        # Track per-row reset buttons for inline updates
        self.reset_buttons = {}

        # --- Initial Load ---
        self.load_and_display_keybinds()

    def update_file_label(self):
        display = self.filename if self.filename else "<no file selected>"
        self.file_label.configure(text=f"Editing: {display}")

    def parse_line(self, line):
        """Parses a single line from the keybinds file and returns a structured dictionary."""
        stripped_line = line.strip()
        
        if not stripped_line:
            return {"type": "empty", "original": line}
        if stripped_line.startswith("//"):
            return {"type": "comment", "original": line}
        
        parts = stripped_line.split(None, 2)
        
        if len(parts) > 1 and parts[0] == "bind":
            if len(parts) == 3:
                return {
                    "type": "bind",
                    "key": parts[1],
                    "action": parts[2],
                    "original": line
                }
        
        # If it's not a bind, comment, or empty, treat it as a generic command
        return {"type": "command", "original": line}

    def load_and_display_keybinds(self):
        """Loads the keybinds file, parses it, and populates the UI."""
        # Clear any existing data and widgets
        self._cancel_batched_build()
        self.keybind_data.clear()
        self.ui_widgets.clear()
        # Clear previous UI rows
        if hasattr(self, "content_frame") and self.content_frame is not None:
            for widget in self.content_frame.winfo_children():
                widget.destroy()

        if not self.filename or not os.path.exists(self.filename):
            initial_dir = os.path.dirname(self.filename) if self.filename else r"C:\\Program Files\\Beyond-All-Reason\\data"
            selected = filedialog.askopenfilename(
                title="Select keybinds file",
                initialdir=initial_dir if os.path.isdir(initial_dir) else os.getcwd(),
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not selected:
                messagebox.showerror("File Not Found", f"Default file not found and no file selected.")
                self.update_file_label()
                return
            self.filename = selected
            self.update_file_label()
        else:
            self.update_file_label()

        try:
            with open(self.filename, "r") as f:
                lines = f.readlines()

            # Parse every line and store it
            for i, line in enumerate(lines):
                parsed = self.parse_line(line)
                # We use the line number (i) as a unique ID
                parsed['id'] = i
                if parsed.get("type") == "bind":
                    # Snapshot the original key for change detection
                    parsed['original_key'] = parsed.get('key', '')
                self.keybind_data.append(parsed)

            # If a defaults file exists, merge in any missing actions as synthetic "unbound" rows
            try:
                default_actions = self._load_default_actions()
            except Exception:
                default_actions = set()
            if default_actions:
                existing_actions = {item.get("action") for item in self.keybind_data if item.get("type") == "bind"}
                missing_actions = [a for a in default_actions if a not in existing_actions]
                # Ensure unique IDs continue from the max existing id
                next_id = (max((it.get('id', -1) for it in self.keybind_data), default=-1) + 1) if self.keybind_data else 0
                for action in sorted(missing_actions):
                    self.keybind_data.append({
                        "type": "bind",
                        "key": "unbound",
                        "action": action,
                        "original": None,
                        "id": next_id,
                        "original_key": None,
                        "synthetic": True,
                    })
                    next_id += 1

            # Now, create the UI elements based on the parsed data in batches
            self.start_populating_ui()
            
        except Exception as e:
            messagebox.showerror("Error Loading File", f"An error occurred: {e}")

    def _load_default_actions(self):
        """Parse `original keys.txt` (if present) and return a set of action strings.

        The defaults file should be placed alongside this script. Only `bind` lines
        are considered; non-bind lines are ignored. Duplicate actions are reduced
        to a single representative action string.
        """
        actions = set()
        self.default_action_to_keys = {}
        if not self.defaults_path or not os.path.exists(self.defaults_path):
            return actions
        with open(self.defaults_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed = self.parse_line(line)
                if parsed.get("type") == "bind":
                    act = parsed.get("action")
                    key = parsed.get("key")
                    if act:
                        actions.add(act)
                        if key:
                            self.default_action_to_keys.setdefault(act, []).append(key)
        return actions

    def _default_key_for_action(self, action: str):
        """Return the first default key for a given action, if any."""
        if not action:
            return None
        keys = self.default_action_to_keys.get(action)
        if keys:
            return keys[0]
        return None

    def start_populating_ui(self):
        """Start building UI rows in batches on a hidden frame, then swap in."""
        self._cancel_batched_build()
        # Sync UI edits back to data so toggling filters won't discard unsaved text
        self._sync_ui_to_data()
        # Clear button mapping; will be rebuilt
        self.reset_buttons.clear()
        # Build filtered/sorted item list
        items = [it for it in self.keybind_data if it.get("type") == "bind"]
        # Apply filters
        if self.show_only_unbound.get():
            items = [it for it in items if (it.get("key", "") or "").strip().lower() in ("", "unbound")]
        if self.show_only_changed.get():
            items = [it for it in items if self._is_changed(it)]
        # Apply sort
        mode = (self.sort_mode.get() or "Original").lower()
        if mode.startswith("unbound"):
            def sort_key(it):
                k = (it.get("key", "") or "").strip().lower()
                is_unbound = 0 if k in ("", "unbound") else 1
                return (is_unbound, (it.get("action") or "").lower(), it.get("id", 0))
            items.sort(key=sort_key)
        elif mode.startswith("action"):
            items.sort(key=lambda it: ((it.get("action") or "").lower(), it.get("id", 0)))
        else:
            items.sort(key=lambda it: it.get("id", 0))
        # Create a new hidden frame to build rows off-screen
        new_frame = ctk.CTkFrame(self.scrollable_frame)
        new_frame.grid_columnconfigure(0, weight=1)
        new_frame.grid_columnconfigure(1, weight=0)
        # Reset UI mapping
        self.ui_widgets.clear()
        # Initialize batch context
        self._build_ctx = {
            "frame": new_frame,
            "index": 0,
            "row_index": 0,
            "items": items,
        }
        # Disable save button while building to avoid partial reads
        try:
            self.save_button.configure(state="disabled")
        except Exception:
            pass
        # Kick off batched building
        self._build_after_id = self.after(1, self._populate_ui_batch)

    def _populate_ui_batch(self):
        ctx = self._build_ctx
        if not ctx:
            return
        frame = ctx["frame"]
        i = ctx["index"]
        row_index = ctx["row_index"]
        items = ctx.get("items", [])
        n = len(items)
        limit = min(i + self._build_batch_size, n)

        while i < limit:
            item = items[i]
            if item.get("type") == "bind":
                # Apply filter if enabled: only show rows whose key is empty or 'unbound'
                action_label = ctk.CTkLabel(frame, text=item.get("action", ""), anchor="w")
                action_label.grid(row=row_index, column=0, sticky="ew", padx=10, pady=2)

                key_entry = ctk.CTkEntry(
                    frame,
                    width=220,
                    placeholder_text="Click and press a key (or type e.g., 1,1)",
                )
                key_text = item.get("key", "") or ""
                key_entry.insert(0, key_text)
                key_entry.grid(row=row_index, column=1, sticky="e", padx=10, pady=2)
                # Prevent free editing; enable only while listening
                try:
                    key_entry.configure(state="disabled")
                except Exception:
                    pass

                self.ui_widgets[item["id"]] = key_entry
                key_entry.bind("<Button-1>", lambda e, entry=key_entry: self.start_listening(entry))

                # Unbind button for this row
                unbind_btn = ctk.CTkButton(
                    frame,
                    text="Unbind",
                    width=70,
                    command=lambda entry=key_entry, it=item: self._unbind_row(entry, it),
                )
                unbind_btn.grid(row=row_index, column=2, sticky="e", padx=(0, 6), pady=2)

                # Reset button if changed or a default is known
                default_key = self._default_key_for_action(item.get("action"))
                cur_key_norm = (item.get("key", "") or "").strip().lower()
                def_norm = (default_key or "").strip().lower()
                show_reset = self._is_changed(item) or (default_key is not None and cur_key_norm != def_norm)
                if show_reset:
                    reset_btn = ctk.CTkButton(
                        frame,
                        text="Reset",
                        width=70,
                        command=lambda entry=key_entry, it=item: self._reset_row(entry, it),
                    )
                    reset_btn.grid(row=row_index, column=3, sticky="e", padx=(0, 10), pady=2)
                    self.reset_buttons[item["id"]] = reset_btn
                else:
                    # Ensure no stale mapping
                    self.reset_buttons.pop(item["id"], None)
                row_index += 1
            i += 1

        # Save progress
        ctx["index"] = i
        ctx["row_index"] = row_index

        if i < n:
            # Schedule next batch
            self._build_after_id = self.after(1, self._populate_ui_batch)
        else:
            # Finished: swap frames in and finalize layout
            try:
                # Remove old content frame
                if self.content_frame and self.content_frame.winfo_exists():
                    self.content_frame.destroy()
            except Exception:
                pass
            self.content_frame = frame
            self.content_frame.pack(anchor="nw")
            self.content_frame.pack_propagate(False)
            self._build_ctx = None
            # Re-enable save button now that UI is ready
            try:
                self.save_button.configure(state="normal")
            except Exception:
                pass
            # Apply width once after full build
            self.after(0, self._apply_content_width)

    def _sync_ui_to_data(self):
        """Update self.keybind_data['key'] values from current UI entries if present."""
        if not self.ui_widgets:
            return
        for item in self.keybind_data:
            if item.get("type") != "bind":
                continue
            entry_widget = self.ui_widgets.get(item.get("id"))
            if entry_widget:
                try:
                    item["key"] = (entry_widget.get() or "").strip()
                except Exception:
                    pass

    def on_toggle_unbound_only(self):
        # Rebuild UI with updated filter, keeping unsaved edits via sync
        self.start_populating_ui()

    def on_toggle_changed_only(self):
        self.start_populating_ui()

    def on_change_sort(self):
        self.start_populating_ui()

    def _is_changed(self, item: dict) -> bool:
        if item.get("type") != "bind":
            return False
        cur = (item.get("key", "") or "").strip().lower()
        orig = item.get("original_key")
        if orig is None:
            # Synthetic default: treated as changed only if user bound it
            return cur not in ("", "unbound")
        return cur != (orig or "").strip().lower()

    def _unbind_row(self, entry, item):
        prev_state = None
        try:
            prev_state = entry.cget("state")
            entry.configure(state="normal")
        except Exception:
            pass
        try:
            entry.delete(0, "end")
        except Exception:
            pass
        try:
            entry.insert(0, "unbound")
        except Exception:
            pass
        try:
            if prev_state:
                entry.configure(state=prev_state)
        except Exception:
            pass
        item["key"] = "unbound"
        # Update UI so Reset button reflects immediately without full rebuild
        self._maybe_refresh_after_row_change(item=item, entry=entry)

    def _reset_row(self, entry, item):
        orig = (item.get("original_key") or "").strip()
        if not orig:
            # For synthetic or missing original, try default
            orig = (self._default_key_for_action(item.get("action")) or "").strip()
        prev_state = None
        try:
            prev_state = entry.cget("state")
            entry.configure(state="normal")
        except Exception:
            pass
        try:
            entry.delete(0, "end")
        except Exception:
            pass
        try:
            entry.insert(0, orig)
        except Exception:
            pass
        try:
            if prev_state:
                entry.configure(state=prev_state)
        except Exception:
            pass
        item["key"] = orig
        # Update UI so Reset button visibility/state reflects immediately
        self._maybe_refresh_after_row_change(item=item, entry=entry)

    def _maybe_refresh_after_row_change(self, item=None, entry=None):
        """Rebuild the UI when filters/sort demand it; otherwise update this row inline."""
        try:
            needs_rebuild = (
                self.show_only_unbound.get()
                or self.show_only_changed.get()
                or (self.sort_mode.get() or "Original") != "Original"
            )
        except Exception:
            needs_rebuild = True
        if needs_rebuild:
            self.start_populating_ui()
            return
        # Inline update of Reset button for the affected row
        if item is not None and entry is not None:
            self._update_row_buttons(entry, item)

    def _update_row_buttons(self, entry, item):
        """Ensure the Reset button for this row is shown/hidden based on current state."""
        try:
            parent = entry.master
            info = entry.grid_info()
            row_index = int(info.get("row", 0))
        except Exception:
            return

        default_key = self._default_key_for_action(item.get("action"))
        cur_key_norm = (item.get("key", "") or "").strip().lower()
        def_norm = (default_key or "").strip().lower()
        show_reset = self._is_changed(item) or (default_key is not None and cur_key_norm != def_norm)

        # Existing reset widget if any
        existing = self.reset_buttons.get(item.get("id"))
        if show_reset:
            if existing and getattr(existing, "winfo_exists", lambda: False)():
                # Ensure it's gridded in the right spot
                try:
                    existing.grid(row=row_index, column=3, sticky="e", padx=(0, 10), pady=2)
                except Exception:
                    pass
            else:
                try:
                    reset_btn = ctk.CTkButton(
                        parent,
                        text="Reset",
                        width=70,
                        command=lambda entry=entry, it=item: self._reset_row(entry, it),
                    )
                    reset_btn.grid(row=row_index, column=3, sticky="e", padx=(0, 10), pady=2)
                    self.reset_buttons[item["id"]] = reset_btn
                except Exception:
                    pass
        else:
            # Hide/destroy if present
            if existing and getattr(existing, "winfo_exists", lambda: False)():
                try:
                    existing.destroy()
                except Exception:
                    pass
            self.reset_buttons.pop(item.get("id"), None)

    def _cancel_batched_build(self):
        try:
            if self._build_after_id is not None:
                self.after_cancel(self._build_after_id)
        except Exception:
            pass
        self._build_after_id = None
        self._build_ctx = None

    # ---- Resize handling / layout throttling ----
    def _init_content_width(self):
        self._apply_content_width()

    def _on_configure(self, event):
        # Debounce layout updates to avoid heavy recalcs during live drag
        if event.widget is self:
            if self._resize_after_id is not None:
                try:
                    self.after_cancel(self._resize_after_id)
                except Exception:
                    pass
            self._resize_after_id = self.after(400, self._apply_content_width)

    def _apply_content_width(self):
        self._resize_after_id = None
        try:
            # Use the inner area width of the scrollable frame if available
            target_width = max(200, int(self.scrollable_frame.winfo_width()) - 20)
        except Exception:
            target_width = 600
        try:
            self.content_frame.configure(width=target_width)
        except Exception:
            pass

    # ---- Key Capture Logic ----
    def start_listening(self, entry):
        # Enter listening mode for this entry; capture the very next keypress anywhere in the app
        self.listening_entry = entry
        # Enable editing while listening
        try:
            entry.configure(state="normal")
        except Exception:
            pass
        try:
            entry.delete(0, "end")
        except Exception:
            pass
        entry.insert(0, "Press keys… (multi-tap supported)")
        # Reset tracked modifiers
        self.active_mods.clear()
        self.saw_alt_press = False
        self.saw_any_nonmod_key = False
        # Prepare multi-tap state
        self._reset_sequence_timer()
        self.sequence_parts = []
        # Bind globally so we catch keys even if the Entry loses focus momentarily
        self.bind_all("<KeyPress>", self.on_key_press)
        # Explicitly bind KeyPress while modifiers are held to ensure delivery on some Tk/Windows paths
        self.bind_all("<Alt-KeyPress>", self.on_key_press)
        self.bind_all("<Control-KeyPress>", self.on_key_press)
        self.bind_all("<Shift-KeyPress>", self.on_key_press)
        self.bind_all("<Meta-KeyPress>", self.on_key_press)
        # Track modifier state explicitly to avoid relying on event.state
        self.bind_all("<KeyPress-Shift_L>", self.on_modifier_press)
        self.bind_all("<KeyPress-Shift_R>", self.on_modifier_press)
        self.bind_all("<KeyRelease-Shift_L>", self.on_modifier_release)
        self.bind_all("<KeyRelease-Shift_R>", self.on_modifier_release)

        self.bind_all("<KeyPress-Control_L>", self.on_modifier_press)
        self.bind_all("<KeyPress-Control_R>", self.on_modifier_press)
        self.bind_all("<KeyRelease-Control_L>", self.on_modifier_release)
        self.bind_all("<KeyRelease-Control_R>", self.on_modifier_release)

        self.bind_all("<KeyPress-Alt_L>", self.on_modifier_press)
        self.bind_all("<KeyPress-Alt_R>", self.on_modifier_press)
        self.bind_all("<KeyRelease-Alt_L>", self.on_modifier_release)
        self.bind_all("<KeyRelease-Alt_R>", self.on_modifier_release)
        # Some platforms/layouts report Alt as Meta; bind these as well
        self.bind_all("<KeyPress-Meta_L>", self.on_modifier_press)
        self.bind_all("<KeyPress-Meta_R>", self.on_modifier_press)
        self.bind_all("<KeyRelease-Meta_L>", self.on_modifier_release)
        self.bind_all("<KeyRelease-Meta_R>", self.on_modifier_release)
        # Prevent the click from placing a caret or inserting characters
        return "break"

    def end_listening(self):
        # Stop capturing keys
        entry = self.listening_entry
        try:
            self.unbind_all("<KeyPress>")
        except Exception:
            pass
        for seq in ("<Alt-KeyPress>", "<Control-KeyPress>", "<Shift-KeyPress>", "<Meta-KeyPress>"):
            try:
                self.unbind_all(seq)
            except Exception:
                pass
        # Unbind modifier trackers
        for seq in (
            "<KeyPress-Shift_L>", "<KeyPress-Shift_R>", "<KeyRelease-Shift_L>", "<KeyRelease-Shift_R>",
            "<KeyPress-Control_L>", "<KeyPress-Control_R>", "<KeyRelease-Control_L>", "<KeyRelease-Control_R>",
            "<KeyPress-Alt_L>", "<KeyPress-Alt_R>", "<KeyRelease-Alt_L>", "<KeyRelease-Alt_R>",
            "<KeyPress-Meta_L>", "<KeyPress-Meta_R>", "<KeyRelease-Meta_L>", "<KeyRelease-Meta_R>",
        ):
            try:
                self.unbind_all(seq)
            except Exception:
                pass
        # Disable editing after listening ends
        if entry is not None:
            try:
                entry.configure(state="disabled")
            except Exception:
                pass
        self.listening_entry = None
        self.active_mods.clear()
        self.saw_alt_press = False
        self.saw_any_nonmod_key = False
        self._reset_sequence_timer()
        self.sequence_parts = None

    def on_key_press(self, event):
        # Only handle when we're in listening mode
        if not self.listening_entry:
            return

        # Mark if a non-modifier key is pressed
        keysym = getattr(event, "keysym", "")
        if keysym not in {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R"}:
            self.saw_any_nonmod_key = True

        key_text = self.format_key_event(event)
        if key_text is None:
            # If unmapped, just ignore and keep listening
            return "break"

        # Multi-tap: accumulate within timeout
        if self.sequence_parts is not None:
            self.sequence_parts.append(key_text)
            seq_text = ",".join(self.sequence_parts)
            entry = self.listening_entry
            try:
                entry.delete(0, "end")
            except Exception:
                pass
            entry.insert(0, seq_text)
            self._reset_sequence_timer()
            self.sequence_after_id = self.after(self.sequence_timeout_ms, self._finalize_sequence)
            return "break"

        # Update the entry with the mapped key text
        entry = self.listening_entry
        try:
            entry.delete(0, "end")
        except Exception:
            pass
        entry.insert(0, key_text)
        self.end_listening()
        # Block the default character insertion into the Entry
        return "break"

    def _finalize_sequence(self):
        # Called when the multi-tap window expires; finish listening
        self.sequence_after_id = None
        self.sequence_parts = None
        self.end_listening()

    def _reset_sequence_timer(self):
        try:
            if self.sequence_after_id is not None:
                self.after_cancel(self.sequence_after_id)
        except Exception:
            pass
        self.sequence_after_id = None

    # ---- Modifier Tracking ----
    def on_modifier_press(self, event):
        keysym = getattr(event, "keysym", "") or ""
        if "Shift" in keysym:
            self.active_mods.add("Shift")
        elif "Control" in keysym:
            self.active_mods.add("Ctrl")
        elif "Alt" in keysym or "Meta" in keysym:
            self.active_mods.add("Alt")
            self.saw_alt_press = True

    def on_modifier_release(self, event):
        keysym = getattr(event, "keysym", "") or ""
        if "Shift" in keysym:
            self.active_mods.discard("Shift")
        elif "Control" in keysym:
            self.active_mods.discard("Ctrl")
        elif "Alt" in keysym or "Meta" in keysym:
            self.active_mods.discard("Alt")

    # ---- Key Event Formatting ----
    def format_key_event(self, event):
        """
        Convert a Tk key event into the game's key string.

        Updated behavior:
        - Always detect modifiers (Ctrl, Alt, Shift) and prefix combos accordingly,
          even for digits/letters/punctuation. Example: "Ctrl+Shift+1".
        - Prefer keysym-based identification over the text character to avoid layout-dependent
          glyphs like '@' or '!' when Shift is held.
        - Map shifted symbol keysyms/characters back to their base number-row keys
          so Shift+2 ("@") becomes base key "2".
        - Keep existing names for specials and numpad keys.
        """

        keysym = getattr(event, "keysym", "") or ""
        char = getattr(event, "char", "") or ""
        # Use tracked modifiers; selectively fall back to event.state
        mods = []
        if "Ctrl" in self.active_mods:
            mods.append("Ctrl")
        if "Alt" in self.active_mods:
            mods.append("Alt")
        if "Shift" in self.active_mods:
            mods.append("Shift")

        # Fallback to event.state for Ctrl/Shift; for Alt use physical key state on Windows
        try:
            state = int(getattr(event, "state", 0) or 0)
        except Exception:
            state = 0
        # Bit masks commonly used by Tk: Shift=0x0001, Control=0x0004, Alt(Mod1)=0x0008
        if "Ctrl" not in mods and (state & 0x0004):
            mods.append("Ctrl")
        # For Alt combos, prefer checking physical key state on Windows to avoid sticky menu Alt
        if (
            "Alt" not in mods
            and keysym not in {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R"}
        ):
            alt_down = False
            try:
                if sys.platform.startswith("win"):
                    VK_MENU = 0x12
                    alt_down = bool(ctypes.windll.user32.GetAsyncKeyState(VK_MENU) & 0x8000)
            except Exception:
                alt_down = False
            if alt_down:
                mods.append("Alt")
            else:
                # Non-Windows fallback: include Alt from state only if we observed Alt press this session
                if (not sys.platform.startswith("win")) and (state & 0x0008) and self.saw_alt_press:
                    mods.append("Alt")
        if "Shift" not in mods and (state & 0x0001):
            mods.append("Shift")
        prefix = "+".join(mods) + ("+" if mods else "")

        # Ignore pure modifier presses
        if keysym in {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R"}:
            return None

        # Numpad keys (Tk uses KP_*)
        if keysym.startswith("KP_"):
            kp_map = {
                "KP_Add": "numpad+",
                "KP_Subtract": "numpad-",
                "KP_Multiply": "numpad*",
                "KP_Divide": "numpad/",
                "KP_Enter": "numpadenter",
                "KP_Decimal": "numpad.",
            }
            if keysym in kp_map:
                return f"{prefix}{kp_map[keysym]}" if mods else kp_map[keysym]
            if keysym.startswith("KP_") and keysym[3:].isdigit():
                base = f"numpad{keysym[3:]}"
                return f"{prefix}{base}" if mods else base

        # Common specials
        specials = {
            "BackSpace": "backspace",
            "Return": "enter",
            "Tab": "tab",
            "Escape": "esc",
            "space": "space",
            "Delete": "delete",
            "Home": "home",
            "End": "end",
            "Prior": "pageup",
            "Next": "pagedown",
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "Insert": "insert",
        }
        if keysym in specials:
            base = specials[keysym]
            return f"{prefix}{base}" if mods else base

        # Function keys (F1..F24)
        if (keysym.startswith("F") and keysym[1:].isdigit() and 1 <= int(keysym[1:]) <= 24):
            return f"{prefix}{keysym}" if mods else keysym

        # Map shifted symbol names/chars back to number-row digits
        sym_to_digit = {
            "exclam": "1", "at": "2", "numbersign": "3", "dollar": "4",
            "percent": "5", "asciicircum": "6", "ampersand": "7", "asterisk": "8",
            "parenleft": "9", "parenright": "0",
        }
        char_sym_to_digit = {
            "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
            "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
        }

        # Decide base key using keysym first, then char
        base_key = None

        # Letters
        if len(keysym) == 1 and keysym.isalpha():
            base_key = f"sc_{keysym.lower()}"
        elif len(char) == 1 and char.isalpha():
            base_key = f"sc_{char.lower()}"
        # Digits from keysym
        elif len(keysym) == 1 and keysym.isdigit():
            base_key = keysym
        # Digits from char
        elif len(char) == 1 and char.isdigit():
            base_key = char
        # Shifted symbols mapped back to digits
        elif keysym in sym_to_digit:
            base_key = sym_to_digit[keysym]
        elif char in char_sym_to_digit:
            base_key = char_sym_to_digit[char]

        # If we resolved a base key by now, return with modifiers if any
        if base_key is not None:
            return f"{prefix}{base_key}" if mods else base_key

        # Space character (when delivered as char)
        if char == " ":
            return f"{prefix}space" if mods else "space"

        # Fallback for other printable punctuation: use sc_<char>
        if char and char.isprintable():
            base_char = char.lower() if char.isalpha() else char
            base = f"sc_{base_char}"
            return f"{prefix}{base}" if mods else base

        # Last resort: normalized keysym
        if keysym:
            base = keysym.lower()
            return f"{prefix}{base}" if mods else base

        return None

    def save_keybinds(self):
        """Saves the current state of the UI back to the text file."""
        try:
            # Ensure in-memory data matches any on-screen edits
            self._sync_ui_to_data()
            with open(self.filename, "w") as f:
                # 1) Start with a global clear so unbound rows actually unbind
                f.write("unbindall\n")
                # 2) Preserve all non-bind lines (comments, other commands) in original order
                for item in self.keybind_data:
                    if item.get("type") != "bind" and item.get("original") is not None:
                        line = item["original"]
                        # Avoid duplicating unbindall if present in original
                        if line.strip().lower().startswith("unbindall"):
                            continue
                        f.write(line)
                # 3) Write current binds for all bound items
                for item in self.keybind_data:
                    if item.get("type") == "bind":
                        new_key = (item.get("key") or "").strip()
                        if new_key.lower() in ("", "unbound"):
                            continue
                        f.write(f"bind          {new_key:<15}  {item['action']}\n")
            
            messagebox.showinfo("Success", f"Keybinds saved to {self.filename}")

        except Exception as e:
            messagebox.showerror("Error Saving File", f"An error occurred: {e}")


if __name__ == "__main__":
    app = KeybindEditorApp()
    app.mainloop()