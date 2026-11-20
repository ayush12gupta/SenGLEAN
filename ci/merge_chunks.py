"""Paste chunk cores (non-overlapping, same grid) into one GeoTIFF without holding the mosaic in memory.
Usage: merge_chunks.py out.tif chunk1.tif chunk2.tif ..."""
import sys

import rasterio
from rasterio.windows import Window

out, files = sys.argv[1], sys.argv[2:]
srcs = [rasterio.open(f) for f in files]
a = srcs[0].transform.a
left = min(s.bounds.left for s in srcs)
top = max(s.bounds.top for s in srcs)
width = round((max(s.bounds.right for s in srcs) - left) / a)
height = round((top - min(s.bounds.bottom for s in srcs)) / a)
prof = {**srcs[0].profile, "driver": "GTiff", "width": width, "height": height, "transform": rasterio.Affine(a, 0, left, 0, -a, top),
        "BIGTIFF": "IF_SAFER"}
with rasterio.open(out, "w", **prof) as o:
    for s in srcs:
        c0, r0 = round((s.bounds.left - left) / a), round((top - s.bounds.top) / a)
        o.write(s.read(), window=Window(c0, r0, s.width, s.height))
print(f"merged {len(srcs)} chunks -> {width}x{height} px")
