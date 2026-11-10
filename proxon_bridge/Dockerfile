# The base image is set here (no build.yaml, which Home Assistant has deprecated). It must be a glibc-based
# image: Nabto's client library needs glibc and libstdc++, which Home Assistant's default Alpine base doesn't have.
FROM python:3.12-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
 && apt-get clean

WORKDIR /app
COPY bridge.py nabto.py registers.py /app/
CMD ["python3", "-u", "/app/bridge.py"]
