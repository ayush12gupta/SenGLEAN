"""Cut a chunk's enhanced raster down to its core (drop the padding), as float32.
Usage: crop_core.py enhanced.tif out.tif x0 y0 x1 y1   (core bounds in the raster's CRS)"""
import sys

import rasterio
from rasterio.windows import Window

src, dst = sys.argv[1:3]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
with rasterio.open(src) as r:
    t = r.transform
    c0, r0 = round((x0 - t.c) / t.a), round((t.f - y1) / -t.e)
    w, h = round((x1 - x0) / t.a), round((y1 - y0) / -t.e)
    assert c0 >= 0 and r0 >= 0 and c0 + w <= r.width and r0 + h <= r.height, "core falls outside the enhanced raster"
    win = Window(c0, r0, w, h)
    prof = {**r.profile, "driver": "GTiff", "width": w, "height": h, "transform": r.window_transform(win),
            "dtype": "float32", "compress": "deflate", "tiled": True, "blockxsize": 256, "blockysize": 256}
    with rasterio.open(dst, "w", **prof) as o:
        o.write(r.read(window=win).astype("float32"))
print(f"core {w}x{h} px at offset ({c0},{r0})")
