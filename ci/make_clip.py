"""Build an 8-band Sentinel-2 raster on a fixed UTM grid: B2,B3,B4,B8 (10 m) + B5,B6,B7,B8A (20 m), nearest-resampled to --res.

Usage: make_clip.py --items ID[,ID] --epsg 32619 --bounds x0 y0 x1 y1 --out clip.tif [--res 10]
Several items (adjacent tiles of one day) are mosaicked; nodata becomes -9999.
"""
import argparse
import os

import odc.stac
import rioxarray  # noqa: F401  (registers the .rio accessor)
from odc.geo.geobox import GeoBox

from s2 import get_items

p = argparse.ArgumentParser()
p.add_argument("--items", required=True)
p.add_argument("--epsg", required=True, type=int)
p.add_argument("--bounds", required=True, nargs=4, type=float)
p.add_argument("--out", required=True)
p.add_argument("--res", type=float, default=10)
a = p.parse_args()

items = get_items(a.items.split(","))
print("scenes:", [i.id for i in items])
bands = ["B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A"]
gbox = GeoBox.from_bbox(tuple(a.bounds), crs=f"EPSG:{a.epsg}", resolution=a.res)
ds = odc.stac.load(items, bands=bands, geobox=gbox, groupby="solar_day")
da = ds[bands].to_array(dim="band").isel(time=0).assign_coords(band=list(range(1, 9))).fillna(-9999)
print("shape (band,y,x):", da.shape, "dtype:", da.dtype)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
da.rio.to_raster(a.out, compress="deflate")
