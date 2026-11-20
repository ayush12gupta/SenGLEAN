"""Build the 8-band, 10 m Sentinel-2 clip SenGLEAN expects: B2,B3,B4,B8 (10 m) + B5,B6,B7,B8A (20 m, nearest-resampled to 10 m).

Mosaics all tiles acquired on --date (YYYY-mm-dd) over the AOI bbox.
Usage: make_clip.py --bbox "minlon minlat maxlon maxlat" --date 2025-09-12 --out data/s2_data_clip.tif
"""
import argparse
import os

import odc.stac
import rioxarray  # noqa: F401  (registers the .rio accessor)

from s2 import parse_bbox, search, usable_days

p = argparse.ArgumentParser()
p.add_argument("--bbox", required=True)
p.add_argument("--date", required=True)
p.add_argument("--out", required=True)
p.add_argument("--max-cloud", type=float, default=100)
a = p.parse_args()

bbox = parse_bbox(a.bbox)
items = usable_days(search(bbox, a.date, a.date, a.max_cloud), bbox).get(a.date)
if not items:
    raise SystemExit(f"no scene covering the AOI on {a.date}")
print("scenes:", [i.id for i in items])

bands = ["B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A"]
ds = odc.stac.load(items, bands=bands, bbox=bbox, resolution=10, groupby="solar_day")
da = ds[bands].to_array(dim="band").isel(time=0).assign_coords(band=list(range(1, 9))).fillna(-9999)
print("shape (band,y,x):", da.shape, "dtype:", da.dtype)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
da.rio.to_raster(a.out, compress="deflate")
