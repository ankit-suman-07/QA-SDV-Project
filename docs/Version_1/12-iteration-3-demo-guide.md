# Iteration 3 Video Demo Guide

## Prerequisites

- Docker Desktop is running.
- The Python virtual environment has been created.
- Project dependencies are installed.
- Eclipse Ditto is available locally.

## Service Ports

| Service | Port |
|---|---:|
| Frontend | 3000 |
| Eclipse Ditto | 8080 |
| Spring Boot backend | 8082 |
| Simulator control API | 8090 |
| Kuksa databroker | 55556 |

## Start the Demo Environment

Start Eclipse Ditto from its deployment directory:

```bash
cd ../tmp/eclipse-ditto/deployment/docker
docker compose up -d
wq

