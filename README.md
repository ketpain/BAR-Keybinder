# Game Keybind Editor

This small CustomTkinter app edits the Beyond All Reason `uikeys.txt` file.

## Click-to-Bind
- Click inside a key field, then press a key.
- Character keys (letters, digits, punctuation like `, -, =, etc.) are recorded as `sc_<char>` (e.g., `sc_a`, `sc_``, `sc_-`).
- Space is recorded as `space`.
- Numpad keys become `numpad0`..`numpad9`, `numpad+`, `numpad-`, `numpad*`, `numpad/`, `numpad.` and `numpadenter`.
- Special keys like Backspace, Enter, Tab, Esc map to `backspace`, `enter`, `tab`, `esc`.
- Function keys are `F1`..`F24`. If you hold modifiers (Ctrl/Alt/Shift) with function keys, they’re captured as `Ctrl+F1`, etc.
- Pure modifier presses (Shift/Ctrl/Alt alone) are ignored—keep listening until a real key is pressed.

## Key Format (sc_ prefix)
- The game’s parser expects letters and most printable characters as `sc_<character>`.
- Examples:
	- `a` → `sc_a`
	- `.` → `sc_.`
	- `` ` `` → `sc_```
	- `-` → `sc_-`
- Digits on the top row are plain `0..9` (not `sc_`).
- Numpad digits are `numpad0..9`.

## Modifiers and Alt Behavior
- Combos are recorded as `Ctrl+...`, `Alt+...`, `Shift+...`, e.g., `Alt+sc_f`, `Ctrl+Alt+1`.
- Alt-only: Press and release Alt with no other keys → `Alt`.
- Alt combos: Hold Alt, press a non-modifier key (e.g., `F`, `1`, `F5`) → `Alt+...` is captured.

### Windows Specifics (Sticky Alt avoidance)
- On Windows, pressing Alt can shift focus to the app menu and leave Alt “sticky” in some toolkits.
- This app avoids that by:
	- Tracking modifier press/release explicitly.
	- Using the physical Alt state via WinAPI (`GetAsyncKeyState(VK_MENU)`) when determining combos.
	- Only binding Alt-alone when Alt was explicitly pressed and released during the listening session.

## Run
```powershell
python .\main.py
```

If you don’t have the dependency installed, install it first:
```powershell
pip install -r requirements.txt
```

## Notes
- The app will try to open the default game file at `C:\\Program Files\\Beyond-All-Reason\\data\\uikeys.txt`. If it’s missing, it prompts you to select a file.
- Saving rewrites `bind` lines with aligned columns while preserving other lines (comments/commands) as-is.

## Troubleshooting
- Alt keeps binding by itself:
	- Click the field, press a non-modifier key — if `Alt` appears alone, ensure you didn’t trigger the Alt-only path (Alt press and release with no other key). The app also checks the real Alt key state to avoid menu-induced stickiness.
- Alt+key not captured:
	- Some keyboards/IMEs intercept certain Alt combos. Try a different character key or function key. The app binds `<Alt-KeyPress>` explicitly to improve reliability.
- Wrong character recorded:
	- The app prefers `keysym` over raw glyphs. Shifted symbols like `@` become base digits with `Shift` (e.g., `Shift+2`). Letters are always `sc_<letter>`.

## Developer Notes
- Key capture entrypoint: `start_listening` binds global handlers and modifier trackers.
- Modifier state is tracked in `self.active_mods`; session flags `self.saw_alt_press` and `self.saw_any_nonmod_key` help disambiguate Alt-only vs combos.
- `format_key_event` is the single place that converts Tk events into game strings:
	- Prioritizes `keysym` to stay layout-agnostic.
	- Normalizes shifted number-row symbols back to digits.
	- Maps numpad, function, and special keys to their expected names.
	- Modifiers are composed from explicit tracking, with Windows Alt verified through `GetAsyncKeyState`.
- Combo reliability: We also bind `<Alt-KeyPress>`, `<Control-KeyPress>`, `<Shift-KeyPress>`, and `<Meta-KeyPress>` to ensure keypress delivery with modifiers.
- To debug, temporarily add prints in `on_key_press` or `format_key_event` (e.g., keysym, state, resolved string).
