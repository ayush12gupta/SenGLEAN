"""Center-crop a GeoTIFF to a square of KM kilometres (keeps georeferencing). Usage: crop_center.py in.tif out.tif KM"""
import sys

import rasterio
from rasterio.windows import Window

src, dst, km = sys.argv[1], sys.argv[2], float(sys.argv[3])
with rasterio.open(src) as r:
    W0, H0 = r.width, r.height
    n = min(int(km * 1000 / abs(r.res[0])), r.width, r.height)
    w = Window((r.width - n) // 2, (r.height - n) // 2, n, n)
    prof = {**r.profile, "driver": "GTiff", "width": n, "height": n, "transform": r.window_transform(w)}
    with rasterio.open(dst, "w", **prof) as o:
        o.write(r.read(window=w))
print(f"cropped {W0}x{H0} -> {n}x{n} px")
