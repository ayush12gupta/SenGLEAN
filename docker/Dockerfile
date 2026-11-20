# Prebuilt environment for the senglean workflow: Python 3.10 (the repo imports distutils), GDAL, the CPU torch stack,
# and a separate venv (/opt/dv) with newer numpy for the Sentinel-2 data scripts.
FROM python:3.10-slim-bookworm
LABEL org.opencontainers.image.source="https://github.com/ayush12gupta/SenGLEAN"
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# git/procps/gawk/zstd: what the actions and workflow steps call (checkout, free, awk, cache)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgdal-dev gdal-bin git procps gawk zstd ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U pip setuptools wheel numpy==1.24.4 \
    && pip install torch==2.0.1+cpu torchvision==0.15.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-build-isolation "GDAL==$(gdal-config --version)" \
    && echo "numpy==1.24.4" > /tmp/c.txt \
    && pip install -c /tmp/c.txt scipy pillow scikit-image opencv-python-headless==4.8.0.74 tqdm pytorch-msssim \
        easydict matplotlib imageio requests psutil click torchmetrics==1.0.1 gdown \
    && python -m venv /opt/dv \
    && /opt/dv/bin/pip install pystac-client planetary-computer odc-stac rioxarray geopandas shapely pyproj \
    && python -c "import numpy, torch, osgeo; torch.from_numpy(numpy.zeros(1)); print('numpy', numpy.__version__, 'torch', torch.__version__)" \
    && /opt/dv/bin/python -c "import odc.stac, rioxarray, geopandas, pyproj; print('data venv ok')" \
    && apt-get purge -y build-essential && apt-get autoremove -y && rm -rf /tmp/c.txt /var/lib/apt/lists/*
