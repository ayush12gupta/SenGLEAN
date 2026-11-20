"""Pick the Sentinel-2 acquisition days for a workflow run and plan the chunks. Emits two GitHub matrices.
Usage: prep_scenes.py BEGIN END AOI CLOUD MAX_SCENES CHUNK_KM TA_KM   (dates YYYYmmdd, AOI 'minlon minlat maxlon maxlat')
"""
import json
import os
import sys

from s2 import aoi_bounds, check_size, chunks, iso, parse_bbox, search, ta_bounds, usable_days, utm_epsg

begin, end, aoi_s, cloud, max_scenes, chunk_km, ta_km = sys.argv[1:8]
bbox = parse_bbox(aoi_s)
check_size(bbox)
if float(ta_km) < 5.2:
    raise SystemExit("ta_km must be >= 5.2 (adaptation uses 512 px patches)")
items = search(bbox, iso(begin), iso(end), float(cloud))
days = usable_days(items, bbox)
if not days:
    raise SystemExit(f"no day in {begin}-{end} fully covers the AOI with <{cloud}% cloud ({len(items)} partial scenes found)")
picked = list(days.items())[: int(max_scenes)]

epsg = utm_epsg(bbox)
aoi = aoi_bounds(bbox, epsg)
ch = chunks(aoi, float(chunk_km))
if len(ch) * len(picked) > 250:
    raise SystemExit(f"{len(ch)} chunks x {len(picked)} days exceeds the 256-job matrix limit; raise chunk_km or lower max_scenes")
ta = ta_bounds(aoi, float(ta_km))
j = lambda b: " ".join(map(str, b))

day_rows, chunk_rows = [], []
for d, v in picked:
    ids = ",".join(i.id for i in v)
    cloud_pct = round(max(i.properties["eo:cloud_cover"] for i in v), 2)
    day_rows.append({"date": d, "cloud": cloud_pct, "items": ids, "epsg": epsg, "aoi": j(aoi), "ta": j(ta)})
    chunk_rows += [{"date": d, "idx": c["idx"], "items": ids, "epsg": epsg, "core": j(c["core"]), "padded": j(c["padded"])} for c in ch]
for r in day_rows:
    print(r)
print(f"{len(days)} usable day(s); running {len(picked)} x {len(ch)} chunk(s); AOI {aoi}; adapt on {ta}")

out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        print(f"DAYS={json.dumps({'include': day_rows})}", file=f)
        print(f"CHUNKS={json.dumps({'include': chunk_rows})}", file=f)
        print(f"DAY_COUNT={len(day_rows)}", file=f)
        print(f"CHUNK_COUNT={len(ch)}", file=f)
