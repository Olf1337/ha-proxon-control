ARG BUILD_FROM=python:3.12-slim-bookworm
FROM ${BUILD_FROM}
# glibc-based image: the Nabto client library needs glibc and libstdc++
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates libstdc++6 \
 && apt-get clean
WORKDIR /app
COPY bridge.py nabto.py registers.py /app/
CMD ["python3", "-u", "/app/bridge.py"]
