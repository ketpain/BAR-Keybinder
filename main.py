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
        self.geometry("800x600")

        # --- Data Storage ---
        # This list will hold our parsed keybind data.
        # Each item will be a dictionary representing one line from the file.
        self.keybind_data = []
        # This dictionary will link a specific keybind's data to its UI entry widget
        self.ui_widgets = {}
        self.filename = r"C:\\Program Files\\Beyond-All-Reason\\data\\uikeys.txt"

        # --- Runtime State ---
        self.listening_entry = None
        self.active_mods = set()  # tracks currently pressed modifiers while listening
        self.saw_alt_press = False
        self.saw_any_nonmod_key = False
        self.DEBUG = False  # set True to print key event debug info

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

        # --- Main Scrollable Frame for Keybinds ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="Keybinds")
        self.scrollable_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

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
        self.keybind_data.clear()
        self.ui_widgets.clear()
        for widget in self.scrollable_frame.winfo_children():
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
                self.keybind_data.append(parsed)

            # Now, create the UI elements based on the parsed data
            self.populate_ui()
            
        except Exception as e:
            messagebox.showerror("Error Loading File", f"An error occurred: {e}")

    def populate_ui(self):
        """Creates and displays the UI widgets for each keybind."""
        for item in self.keybind_data:
            if item["type"] == "bind":
                # Create a frame for each row to hold the label and entry
                row_frame = ctk.CTkFrame(self.scrollable_frame)
                row_frame.pack(fill="x", padx=5, pady=2)

                # The action is on the left
                action_label = ctk.CTkLabel(row_frame, text=item["action"], anchor="w")
                action_label.pack(side="left", fill="x", expand=True, padx=10)

                # The key entry field is on the right
                key_entry = ctk.CTkEntry(row_frame, width=200, placeholder_text="Click and press a key")
                key_entry.insert(0, item["key"])
                key_entry.pack(side="right", padx=10)

                # Store the entry widget using the unique ID so we can retrieve its value later
                self.ui_widgets[item["id"]] = key_entry

                # Bind click/focus to start listening for a key press for this entry
                key_entry.bind("<Button-1>", lambda e, entry=key_entry: self.start_listening(entry))

    # ---- Key Capture Logic ----
    def start_listening(self, entry):
        # Enter listening mode for this entry; capture the very next keypress anywhere in the app
        self.listening_entry = entry
        try:
            entry.delete(0, "end")
        except Exception:
            pass
        entry.insert(0, "Press any key…")
        # Reset tracked modifiers
        self.active_mods.clear()
        self.saw_alt_press = False
        self.saw_any_nonmod_key = False
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
        self.listening_entry = None
        self.active_mods.clear()
        self.saw_alt_press = False
        self.saw_any_nonmod_key = False

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

    def on_modifier_press(self, event):
        keysym = getattr(event, "keysym", "")
        if keysym in ("Shift_L", "Shift_R"):
            self.active_mods.add("Shift")
        elif keysym in ("Control_L", "Control_R"):
            self.active_mods.add("Ctrl")
        elif keysym in ("Alt_L", "Alt_R", "Meta_L", "Meta_R"):
            self.active_mods.add("Alt")
            self.saw_alt_press = True
        return "break"

    def on_modifier_release(self, event):
        keysym = getattr(event, "keysym", "")
        # If user pressed only Alt (or Meta) and released it while listening, bind it as 'alt'
        if self.listening_entry and keysym in ("Alt_L", "Alt_R", "Meta_L", "Meta_R"):
            prior_mods = set(self.active_mods)
            # If Alt was the only active modifier, treat as Alt-only bind
            if prior_mods == {"Alt"} and self.saw_alt_press and not self.saw_any_nonmod_key:
                entry = self.listening_entry
                try:
                    entry.delete(0, "end")
                except Exception:
                    pass
                entry.insert(0, "Alt")
                self.end_listening()
                return "break"
        if keysym in ("Shift_L", "Shift_R"):
            self.active_mods.discard("Shift")
        elif keysym in ("Control_L", "Control_R"):
            self.active_mods.discard("Ctrl")
        elif keysym in ("Alt_L", "Alt_R", "Meta_L", "Meta_R"):
            self.active_mods.discard("Alt")
        return "break"

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
            with open(self.filename, "w") as f:
                # Iterate through our original structured data
                for item in self.keybind_data:
                    if item["type"] == "bind":
                        # If it's a bind, get the potentially modified key from the UI
                        entry_widget = self.ui_widgets.get(item["id"])
                        if entry_widget:
                            new_key = entry_widget.get()
                            # Reconstruct the line with nice formatting
                            # The f-string formatting ensures columns align
                            new_line = f"bind          {new_key:<15}  {item['action']}\n"
                            f.write(new_line)
                        else:
                            # Fallback to original if something went wrong
                            f.write(item["original"])
                    else:
                        # For all other line types, write the original line back
                        f.write(item["original"])
            
            messagebox.showinfo("Success", f"Keybinds saved to {self.filename}")

        except Exception as e:
            messagebox.showerror("Error Saving File", f"An error occurred: {e}")


if __name__ == "__main__":
    app = KeybindEditorApp()
    app.mainloop()