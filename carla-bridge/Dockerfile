# CARLA 0.9.15 Python client. The wheel exists only for x86_64 Linux and
# Windows, so build and run for linux/amd64 (emulated on Apple Silicon).
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip libjpeg8 libtiff5 libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir carla==0.9.15

WORKDIR /bridge
COPY src/ /bridge/
CMD ["python3", "fleet_runner.py"]
