"""Pick the Sentinel-2 acquisition days for a workflow run and emit a GitHub matrix.
Usage: prep_scenes.py BEGIN END AOI CLOUD MAX_SCENES   (dates YYYYmmdd, AOI 'minlon minlat maxlon maxlat')
"""
import json
import os
import sys

from s2 import check_size, iso, parse_bbox, search, usable_days

begin, end, aoi, cloud, max_scenes = sys.argv[1:6]
bbox = parse_bbox(aoi)
check_size(bbox)
items = search(bbox, iso(begin), iso(end), float(cloud))
days = usable_days(items, bbox)
if not days:
    raise SystemExit(f"no day in {begin}-{end} fully covers the AOI with <{cloud}% cloud ({len(items)} partial scenes found)")
picked = list(days.items())[: int(max_scenes)]
matrix = {"include": [{"date": d, "cloud": round(max(i.properties["eo:cloud_cover"] for i in v), 2), "tiles": len(v)} for d, v in picked]}
for m in matrix["include"]:
    print(m)
print(f"{len(days)} usable day(s); running {len(picked)}")
out = os.environ.get("GITHUB_OUTPUT")
if out:
    with open(out, "a") as f:
        print(f"MATRIX={json.dumps(matrix)}", file=f)
        print(f"SCENE_COUNT={len(picked)}", file=f)
