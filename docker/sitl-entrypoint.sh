#!/bin/bash
# ArduPilot SITL entrypoint
# Starts arducopter in SITL mode + mavproxy to forward MAVLink to UDP 14540
set -e

SITL_HOME="${SITL_HOME:-47.3977,8.5456,488,180}"
SITL_OUT="${SITL_OUT:-udpout:host.docker.internal:14540}"

echo "[sitl-entrypoint] Starting ArduCopter SITL"
echo "  home    : $SITL_HOME"
echo "  MAVLink : $SITL_OUT"

# Start arducopter in background on TCP 5760
arducopter \
    --model copter \
    --home "${SITL_HOME}" \
    --speedup 1 \
    --defaults /ardupilot/Tools/autotest/default_params/copter.parm \
    -I 0 &
ARDUPILOT_PID=$!

echo "[sitl-entrypoint] ArduCopter PID=$ARDUPILOT_PID"
echo "[sitl-entrypoint] Forwarding MAVLink via mavproxy ..."

# Wait for arducopter to bind its TCP port
sleep 3

# Forward: TCP 5760 (arducopter) -> UDP $SITL_OUT (mavsdk_server)
mavproxy.py \
    --master tcp:127.0.0.1:5760 \
    --out "${SITL_OUT}" \
    --out udpbcast:14550 \
    --no-state \
    --daemon &

echo "[sitl-entrypoint] MAVProxy running, SITL ready on UDP 14540"

# Keep container alive until arducopter exits
wait $ARDUPILOT_PID
