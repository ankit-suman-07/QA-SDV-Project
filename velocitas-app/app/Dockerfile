# syntax=docker/dockerfile:1.2

FROM --platform=$TARGETPLATFORM \
    ghcr.io/eclipse-velocitas/devcontainer-base-images/python:v0.4

COPY ./.velocitas.json /workspace/.velocitas.json
COPY ./.velocitas-lock.json \
    /workspace/.velocitas-lock.json
COPY ./app /workspace/app

RUN pip3 install --no-cache-dir \
    -r /workspace/app/requirements.txt

RUN pip3 install \
    --no-cache-dir \
    --no-deps \
    kuksa_client==0.5.1

RUN pip3 install \
    --no-cache-dir \
    --force-reinstall \
    --no-deps \
    grpcio==1.68.0

WORKDIR /workspace

RUN velocitas init

ENV PYTHONPATH="/workspace/gen/vehicle_model:/workspace/app/src"

WORKDIR /workspace/app

LABEL org.opencontainers.image.source="https://github.com/ankit-suman-07/QA-SDV-Project"
LABEL org.eclipse.velocitas.vehicle-app="AutonomousHealthApp"

CMD ["python3", "src/main.py"]