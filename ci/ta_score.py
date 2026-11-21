"""Score generator checkpoints on a raster with the self-supervised adaptation reference (degrade, then reconstruct).
Run from LightSenGLEAN/Testing with PYTHONPATH=<repo root>:
    python ../../ci/ta_score.py raster.tif name=ckpt.pt [name=ckpt.pt ...]
Prints a markdown table (mean PSNR/SSIM overall, centre patch, corner patches) with the bicubic baseline, and writes scores.csv."""
import csv
import sys

import numpy as np
import torch
from pytorch_msssim import SSIM
from torch import nn

from datasets.patch_data_all_norm import TestData_TA_single
from networks.glean import LightSenGLEANStyleGANv2
from sensor import Sensor
from utils import psnr

raster, variants = sys.argv[1], [a.split("=", 1) for a in sys.argv[2:]]
torch.set_grad_enabled(False)
data = TestData_TA_single(raster, Sensor("S2"), 512)
n = len(data)
side = int(round(n ** 0.5))
ssim = SSIM(data_range=1, size_average=True, channel=8)
rows = []  # (variant, patch, psnr, ssim)


def score(name, fake_fn):
    torch.manual_seed(0)  # the generator injects noise; fix it so variants are comparable
    for i in range(n):
        ms, ms_rgb, ms_up, ms_interp = [t.unsqueeze(0) for t in data[i]]
        fake = fake_fn(ms, ms_rgb, ms_interp)
        rows.append((name, i, float(psnr(fake, ms_up)), float(ssim(fake, ms_up))))
        print(name, i, f"psnr={rows[-1][2]:.2f} ssim={rows[-1][3]:.4f}", flush=True)


score("bicubic", lambda ms, rgb, bic: bic)
for name, ckpt in variants:
    net = nn.DataParallel(LightSenGLEANStyleGANv2(64, 256, 4, 64, 23, rgb_channels=4))
    net.load_state_dict(torch.load(ckpt, map_location="cpu"))  # train mode, as in adaptation and inference
    score(name, lambda ms, rgb, bic: net(ms, rgb))

with open("scores.csv", "w", newline="") as f:
    csv.writer(f).writerows([("variant", "patch", "psnr", "ssim"), *rows])

centre = {(side // 2) * side + side // 2}
corners = {0, side - 1, n - side, n - 1}
names = ["bicubic"] + [v[0] for v in variants]
mean = lambda name, idx, col: np.mean([r[col] for r in rows if r[0] == name and (idx is None or r[1] in idx)])
print("\n| variant | PSNR all | PSNR centre | PSNR corners | SSIM all |\n|---|---|---|---|---|")
for nm in names:
    print(f"| {nm} | {mean(nm, None, 2):.2f} | {mean(nm, centre, 2):.2f} | {mean(nm, corners, 2):.2f} | {mean(nm, None, 3):.4f} |")
