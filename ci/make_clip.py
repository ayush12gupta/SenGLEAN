"""Build the 8-band, 10 m Sentinel-2 clip SenGLEAN expects: B2,B3,B4,B8 (10 m) + B5,B6,B7,B8A (20 m, nearest-resampled to 10 m).

Extent = bounds of the AOI geojson. Picks the least-cloudy scene that fully covers it.
Usage: python make_clip.py --aoi ci/fredericton_aoi.geojson --start 2025-06-01 --end 2025-09-15 --out data/s2_data_clip.tif
"""
import argparse
import geopandas as gpd
import odc.stac
import planetary_computer
import pystac_client
import rioxarray  # noqa: F401  (registers the .rio accessor)
from shapely.geometry import box, shape

p = argparse.ArgumentParser()
p.add_argument("--aoi", required=True)
p.add_argument("--start", required=True)
p.add_argument("--end", required=True)
p.add_argument("--out", required=True)
p.add_argument("--max-cloud", type=float, default=10)
a = p.parse_args()

bbox = list(gpd.read_file(a.aoi).to_crs(4326).total_bounds)
catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace
)
items = catalog.search(
    collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{a.start}/{a.end}",
    query={"eo:cloud_cover": {"lt": a.max_cloud}},
).item_collection()
full = [i for i in items if shape(i.geometry).contains(box(*bbox))]
if not full:
    raise SystemExit(f"no scene fully covering {bbox} with <{a.max_cloud}% cloud in {a.start}..{a.end} ({len(items)} partial)")
item = min(full, key=lambda i: i.properties["eo:cloud_cover"])
print("scene:", item.id, "cloud:", item.properties["eo:cloud_cover"])

bands = ["B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A"]
ds = odc.stac.load([item], bands=bands, bbox=bbox, resolution=10)
da = ds[bands].to_array(dim="band").isel(time=0).assign_coords(band=list(range(1, 9))).fillna(-9999)
print("shape (band,y,x):", da.shape, "dtype:", da.dtype)
da.rio.to_raster(a.out, compress="deflate")
