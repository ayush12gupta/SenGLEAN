"""Crop a GeoTIFF by pixel window (keeps georeferencing). Usage: crop_px.py in.tif out.tif COL ROW SIZE"""
import sys

import rasterio
from rasterio.windows import Window

src, dst, col, row, size = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:6])
with rasterio.open(src) as r:
    win = Window(col, row, size, size)
    assert col + size <= r.width and row + size <= r.height, f"window outside {r.width}x{r.height}"
    prof = {**r.profile, "driver": "GTiff", "width": size, "height": size, "transform": r.window_transform(win)}
    with rasterio.open(dst, "w", **prof) as o:
        o.write(r.read(window=win))
print(f"cropped {size}x{size} px at ({col},{row})")
