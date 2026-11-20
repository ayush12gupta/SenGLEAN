"""Shared Sentinel-2 (Planetary Computer) helpers for the CI scripts."""
import math
from collections import defaultdict
from datetime import datetime, timedelta

import planetary_computer
import pystac_client
from shapely.geometry import box, shape
from shapely.ops import unary_union

URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
MIN_KM, MAX_KM = 5.5, 15  # adaptation samples 512 px (5.1 km) patches; 13 km is the largest size tested


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
                         "(larger areas need chunked inference, not implemented yet; smaller ones are too little for adaptation)")


def iso(d):  # YYYYmmdd -> YYYY-mm-dd
    return datetime.strptime(d, "%Y%m%d").date().isoformat()


def search(bbox, start, end, max_cloud):
    cat = pystac_client.Client.open(URL, modifier=planetary_computer.sign_inplace)
    return cat.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start}T00:00:00Z/{end}T23:59:59Z",
                      query={"eo:cloud_cover": {"lt": max_cloud}}).item_collection()


def usable_days(items, bbox):
    """{date: [items]} for days whose tiles together cover bbox, least cloudy first.
    Tiles of one day are mosaicked by odc.stac (groupby solar_day)."""
    by_day = defaultdict(list)
    for i in items:
        by_day[i.datetime.date().isoformat()].append(i)
    cover = box(*bbox)
    ok = {}
    for d, v in by_day.items():
        single = [i for i in v if shape(i.geometry).buffer(5e-4).contains(cover)]
        if single:  # one tile covers the AOI: use only the least cloudy one, no mosaic seam
            ok[d] = [min(single, key=lambda i: i.properties["eo:cloud_cover"])]
        elif unary_union([shape(i.geometry) for i in v]).buffer(5e-4).contains(cover):  # 5e-4 deg ~ 50 m: closes hairline tile gaps
            ok[d] = v
    return dict(sorted(ok.items(), key=lambda kv: max(i.properties["eo:cloud_cover"] for i in kv[1])))
