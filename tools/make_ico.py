import os
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow is required. Install with: pip install Pillow")
    raise

ROOT = Path(__file__).resolve().parents[1]
src_png = ROOT / "icon.png"
dst_dir = ROOT / "assets"
dst_dir.mkdir(exist_ok=True)
dst_ico = dst_dir / "icon.ico"

if not src_png.exists():
    raise FileNotFoundError(f"Source PNG not found: {src_png}")

img = Image.open(src_png).convert("RGBA")
# Create a multi-resolution ICO for best Windows results
sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
icons = [img.resize(sz, Image.LANCZOS) for sz in sizes]

# Pillow expects the base image; additional sizes via 'sizes' kw
icons[0].save(dst_ico, format='ICO', sizes=sizes)
print(f"Wrote {dst_ico} with sizes: {sizes}")
