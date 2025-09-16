# BAR Keybind Editor (Beyond All Reason)

A simple, user-friendly tool to edit your Beyond All Reason keybinds (`uikeys.txt`). No config syntax needed — just double‑click and press keys.

If you're missing commands, the program parses commands from the (default keys.txt) which is found _interal/defaults/default keys.txt - so just bind the commands and give it a throw away hotkey or use what you would want.

## Regular Users
- To run the app, just run the .exe like any normal program if you download it from the releases page.

# Disclaimer
- I do not intend to maintain this at all. It is mostly just for convenience for my friends and I, since chaning keybinds is quite a hassle currently.

## Quick Start (Windows)
- Install Python and dependencies:
  ```powershell
  pip install -r requirements.txt
  ```
- Run the app:
  ```powershell
  python .\main.py
  ```

The editor will try to open your game keybind file at `C:\Program Files\Beyond-All-Reason\data\uikeys.txt`. If it can’t, you’ll be prompted to pick a file.

## Edit Keys Fast
- Double‑click a Key cell to capture a new shortcut.
- Press the key (or key combo) you want. The app handles letters, numbers, function keys, numpad, arrows, and common symbols automatically.
- Multi‑tap is supported: pause briefly to separate taps (e.g., `B,B` or `Shift+B,Shift+B`).
- Use the “Use Any (ignore extra modifiers)” checkbox to record flexible shortcuts:
  - `Any+K` means K works with any mix of Ctrl/Alt/Shift.
  - `Any+shift` (or `Any+ctrl`, `Any+alt`) means “that modifier is down, others don’t matter.”

## Helpful Tools in the UI
- Show unbound only: filters to actions that currently have no key.
- Show changed only: filters to actions that differ from the defaults/original.
- Sorting: Original order, alphabetical (Action A→Z), or “Unbound first”.
- Unbind: clears the key for that action.
- Reset: restores the game default (if known) or your original key.

## Save vs Activate
- Save Changes: writes to the file you’re currently editing (a preset, or your game file if that’s what you opened).
- Activate to Game: writes the current keys directly to the game’s `uikeys.txt` (and creates a `.bak` backup if a file exists).

Tip: Keep multiple presets anywhere (e.g., Documents). Open one, tweak, then click “Activate to Game”.

## Defaults and Duplicates
- The app reads built‑in defaults from `default keys.txt`. If a default action is missing in your file, it appears as “unbound” so you can quickly fill it in.
- Duplicate keys are highlighted, so you can resolve conflicts at a glance.

## Common Questions
- I can’t save to `C:\Program Files...`:
  - Windows may block writes there. Either run the app as Administrator or save to a writable location and use “Activate to Game”.
- My key shows as `Any+...` — what does that mean?
  - It’s a flexible shortcut: the extra modifiers don’t matter. Great for binds that should work with or without Ctrl/Alt/Shift.
- A combo won’t capture:
  - Some layouts or IMEs may intercept certain combos. Try a different key or use `Any+...` for flexibility.

## Optional: Dark Mode
If `pyqtdarktheme` is installed (included in `requirements.txt`), the app uses a modern dark theme automatically.

## Advanced (Optional): Portable EXE
If you prefer a single executable, you can build one with PyInstaller. From a PowerShell in the project folder:
```powershell
pip install pyinstaller
pyinstaller .\BAR-Keybinder.spec --noconfirm
```
The EXE will be in `dist\BAR-Keybinder.exe`.

That’s it — happy keybinding!
