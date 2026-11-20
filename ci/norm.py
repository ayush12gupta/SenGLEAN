"""Per-band normalisation range for the whole AOI, from a coarse clip (nodata excluded). Usage: norm.py coarse.tif norm.json
Same 1-99 percentile +-100 rule the inference code applies per raster, but shared by every chunk."""
import json
import sys

import numpy as np
import rasterio

with rasterio.open(sys.argv[1]) as r:
    bands = r.read().astype("float64")
norm = []
for b in bands:
    lo, hi = np.percentile(b[b > 0], [1, 99])
    norm.append([max(0.0, float(lo) - 100), float(hi) + 100])
json.dump(norm, open(sys.argv[2], "w"))
print(np.round(norm))
