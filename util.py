import os
import sys


def resource_path(*relative_parts: str) -> str:
    """Return an absolute path to bundled resources.

    Works both in development and when frozen by PyInstaller (onefile/onedir).
    Usage: resource_path("assets", "icon.ico") or resource_path("default keys.txt").
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    # Allow passing a single path string with separators
    if len(relative_parts) == 1 and ("/" in relative_parts[0] or "\\" in relative_parts[0]):
        candidate = os.path.join(base, relative_parts[0])
    else:
        candidate = os.path.join(base, *relative_parts)

    # If the candidate is a directory and the last part looks like a file, try to find it within
    last = relative_parts[-1] if relative_parts else ""
    if os.path.isdir(candidate) and last and not last.endswith(('/', '\\')):
        possible = os.path.join(candidate, last)
        if os.path.exists(possible):
            return possible
    return candidate
