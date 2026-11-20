"""Average generator checkpoints that were fine-tuned from the same weights. Usage: avg_ckpt.py out.pt in1.pt in2.pt ..."""
import sys

import torch

out, files = sys.argv[1], sys.argv[2:]
sds = [torch.load(f, map_location="cpu") for f in files]
avg = {k: (torch.stack([sd[k].float() for sd in sds]).mean(0).to(v.dtype) if v.is_floating_point() else v)
       for k, v in sds[0].items()}
torch.save(avg, out)
print(f"averaged {len(files)} checkpoints, {len(avg)} tensors -> {out}")
