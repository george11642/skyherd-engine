# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# SkyHerd SITL image — ArduPilot Copter SITL on UDP 14540
#
# FAST PATH (recommended): Use a pre-built image from Docker Hub when
# network is available.  The docker-compose.sitl.yml file references
# ardupilot/ardupilot-sitl if SITL_IMAGE is set (see compose file).
#
# BUILD PATH (offline / CI): Builds ArduPilot from source with ccache so
# repeat builds complete in ~3 min instead of 25-40 min.
#
# Usage:
#   docker build --build-arg ARDUPILOT_TAG=Copter-4.5.7 \
#                -f docker/sitl.Dockerfile -t skyherd-sitl .
# ---------------------------------------------------------------------------

FROM ubuntu:22.04 AS ardupilot-build

ARG ARDUPILOT_TAG=Copter-4.5.7
ARG DEBIAN_FRONTEND=noninteractive

# ---- system deps ----
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
        git python3 python3-dev python3-pip \
        build-essential gcc-arm-none-eabi \
        libxml2-dev libxslt-dev zlib1g-dev \
        ccache \
        ca-certificates \
        wget curl \
    && rm -rf /var/lib/apt/lists/*

# ---- ccache (speeds repeated builds from ~30 min to ~3 min) ----
ENV PATH="/usr/lib/ccache:$PATH"
ENV CCACHE_DIR=/root/.ccache

# Clone ArduPilot at the pinned tag (shallow, single-branch — 10x faster)
WORKDIR /ardupilot
RUN --mount=type=cache,target=/root/.ccache \
    git clone --depth=1 --branch="${ARDUPILOT_TAG}" \
        https://github.com/ArduPilot/ardupilot.git . \
    && git submodule update --init --recursive --depth=1 \
    && Tools/environment_install/install-prereqs-ubuntu.sh -y \
    && ./waf configure --board sitl \
    && ./waf --mount=type=cache,target=/root/.ccache copter \
    && ccache -s

# ---------------------------------------------------------------------------
# Runtime image — minimal footprint
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
        python3 python3-pip \
        libxml2 libxslt1.1 \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir MAVProxy pymavlink

# Copy the built ArduCopter binary
COPY --from=ardupilot-build /ardupilot/build/sitl/bin/arducopter /usr/local/bin/arducopter

# Create default home directory for SITL (Zurich Airfield, ArduPilot default)
WORKDIR /sitl
RUN mkdir -p /sitl/logs

# SITL home lat=47.3977 lon=8.5456 alt=488 heading=180 (Zurich matches e2e waypoints)
ENV SITL_HOME="47.3977,8.5456,488,180"
# UDP output — mavsdk_server listens here
ENV SITL_OUT="udpout:host.docker.internal:14540"

# Expose MAVLink UDP port
EXPOSE 14540/udp
EXPOSE 5760/tcp

COPY docker/sitl-entrypoint.sh /sitl-entrypoint.sh
RUN chmod +x /sitl-entrypoint.sh

ENTRYPOINT ["/sitl-entrypoint.sh"]
