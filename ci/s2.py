"""Shared Sentinel-2 (Planetary Computer) helpers for the CI scripts."""
import math
from math import ceil, floor
from collections import defaultdict
from datetime import datetime, timedelta

import planetary_computer
import pystac_client
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely.ops import unary_union

URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
MIN_KM, MAX_KM = 5.5, 40  # adaptation samples 512 px (5.1 km) patches; larger AOIs are split into chunks


def parse_bbox(s):
    b = [float(x) for x in s.split()]
    if len(b) != 4 or b[0] >= b[2] or b[1] >= b[3]:
        raise SystemExit(f"aoi must be 'minlon minlat maxlon maxlat', got: {s!r}")
    return b


def size_km(b):
    return (b[2] - b[0]) * 111.32 * math.cos(math.radians((b[1] + b[3]) / 2)), (b[3] - b[1]) * 111.32


def check_size(b):
    w, h = size_km(b)
    if min(w, h) < MIN_KM or max(w, h) > MAX_KM:
        raise SystemExit(f"AOI is {w:.1f} x {h:.1f} km; each side must be {MIN_KM}-{MAX_KM} km "
                         "(smaller ones are too little for adaptation)")


def iso(d):  # YYYYmmdd -> YYYY-mm-dd
    return datetime.strptime(d, "%Y%m%d").date().isoformat()


def search(bbox, start, end, max_cloud):
    cat = pystac_client.Client.open(URL, modifier=planetary_computer.sign_inplace)
    return cat.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start}T00:00:00Z/{end}T23:59:59Z",
                      query={"eo:cloud_cover": {"lt": max_cloud}}).item_collection()


def usable_days(items, bbox, buffer=0.006):
    """{date: [items]} for days whose tiles together cover bbox, least cloudy first.
    Tiles of one day are mosaicked by odc.stac (groupby solar_day)."""
    by_day = defaultdict(list)
    for i in items:
        by_day[i.datetime.date().isoformat()].append(i)
    cover = box(bbox[0] - buffer, bbox[1] - buffer, bbox[2] + buffer, bbox[3] + buffer)  # ~600 m: chunk padding must be covered too
    ok = {}
    for d, v in by_day.items():
        single = [i for i in v if shape(i.geometry).buffer(5e-4).contains(cover)]
        if single:  # one tile covers the AOI: use only the least cloudy one, no mosaic seam
            ok[d] = [min(single, key=lambda i: i.properties["eo:cloud_cover"])]
        elif unary_union([shape(i.geometry) for i in v]).buffer(5e-4).contains(cover):  # 5e-4 deg ~ 50 m: closes hairline tile gaps
            ok[d] = v
    return dict(sorted(ok.items(), key=lambda kv: max(i.properties["eo:cloud_cover"] for i in kv[1])))


def get_items(ids):
    cat = pystac_client.Client.open(URL, modifier=planetary_computer.sign_inplace)
    items = list(cat.search(collections=["sentinel-2-l2a"], ids=ids).items())
    if len(items) != len(ids):
        raise SystemExit(f"expected {len(ids)} scenes, found {len(items)}")
    return items


# ---- planning on a fixed 10 m UTM grid, so every chunk and the final mosaic share pixel edges ----
def utm_epsg(b):
    return (32600 if (b[1] + b[3]) / 2 >= 0 else 32700) + int(((b[0] + b[2]) / 2 + 180) // 6) + 1


def aoi_bounds(bbox, epsg, res=10):
    t = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = zip(*[t.transform(x, y) for x in (bbox[0], bbox[2]) for y in (bbox[1], bbox[3])])
    return [floor(min(xs) / res) * res, floor(min(ys) / res) * res, ceil(max(xs) / res) * res, ceil(max(ys) / res) * res]


def _split(lo, hi, n, res=10):  # n near-equal pieces, edges on the res grid (no sliver chunks)
    return [lo + round((hi - lo) / n * k / res) * res for k in range(n + 1)]


def chunks(aoi, chunk_km, pad_m=500):
    nx, ny = ceil((aoi[2] - aoi[0]) / (chunk_km * 1000)), ceil((aoi[3] - aoi[1]) / (chunk_km * 1000))
    xe, ye = _split(aoi[0], aoi[2], nx), _split(aoi[1], aoi[3], ny)
    out = []
    for j in range(ny):
        for i in range(nx):
            core = [xe[i], ye[j], xe[i + 1], ye[j + 1]]
            out.append({"idx": len(out), "core": core, "padded": [core[0] - pad_m, core[1] - pad_m, core[2] + pad_m, core[3] + pad_m]})
    return out


def ta_bounds(aoi, km, res=10):  # centered crop the model adapts on
    cx, cy, h = (aoi[0] + aoi[2]) / 2, (aoi[1] + aoi[3]) / 2, km * 500
    lim = [max(aoi[0], cx - h), max(aoi[1], cy - h), min(aoi[2], cx + h), min(aoi[3], cy + h)]
    return [round(v / res) * res for v in lim]


def bounds_to_ll(b, epsg):  # UTM bounds -> lon/lat bbox for STAC search
    t = Transformer.from_crs(epsg, 4326, always_xy=True)
    pts = [t.transform(x, y) for x in (b[0], b[2]) for y in (b[1], b[3])]
    xs, ys = zip(*pts)
    return [min(xs), min(ys), max(xs), max(ys)]
