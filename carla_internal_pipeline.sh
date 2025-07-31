#!/bin/bash

# Internal CARLA pipeline script - runs inside apptainer container
# Usage: carla_internal_pipeline.sh <port> <duration> <recording_file> <output_dir> <replay_mode>

set -e  # Exit on any error

CARLA_PORT=$1
RECORDING_DURATION=$2
RECORDING_FILE=$3
OUTPUT_DIR=$4
REPLAY_MODE=$5

echo "=== CARLA Internal Pipeline Started ==="
echo "Port: $CARLA_PORT"
echo "Duration: $RECORDING_DURATION seconds"
echo "Recording file: $RECORDING_FILE"
echo "Output directory: $OUTPUT_DIR"
echo "Replay mode: $REPLAY_MODE"

# Function to check if CARLA server is running
check_carla_server() {
    python3 -c "
import carla
import sys
try:
    client = carla.Client('localhost', $CARLA_PORT)
    client.set_timeout(2.0)
    world = client.get_world()
    print('CARLA server is ready')
    sys.exit(0)
except Exception as e:
    print(f'CARLA server not ready: {e}')
    sys.exit(1)
"
}

# Function to wait for CARLA server
wait_for_carla_server() {
    echo "Waiting for CARLA server to be ready..."
    local attempts=0
    local max_attempts=30  # 30 seconds timeout
    
    while [ $attempts -lt $max_attempts ]; do
        if check_carla_server; then
            echo "CARLA server is ready!"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
        echo "Waiting... ($attempts/$max_attempts)"
    done
    
    echo "ERROR: CARLA server failed to start within 30 seconds"
    return 1
}

# Start CARLA server in background
echo "Starting CARLA server..."
/home/carla/CarlaUE4.sh -RenderOffScreen -nosound -carla-port=$CARLA_PORT &
CARLA_SERVER_PID=$!

# Set up cleanup trap
cleanup() {
    echo "Cleaning up CARLA server..."
    if kill -0 $CARLA_SERVER_PID 2>/dev/null; then
        kill -TERM $CARLA_SERVER_PID 2>/dev/null || true
        sleep 2
        if kill -0 $CARLA_SERVER_PID 2>/dev/null; then
            kill -KILL $CARLA_SERVER_PID 2>/dev/null || true
        fi
    fi
    echo "Cleanup completed"
}
trap cleanup EXIT

# Wait for CARLA server to be ready
if ! wait_for_carla_server; then
    echo "Failed to start CARLA server"
    exit 1
fi

# Step 1: Record simulation
echo "=== Step 1: Recording simulation ==="
python3 src/recording/record_replay_logs.py record --duration $RECORDING_DURATION --file "$RECORDING_FILE"

if [ $? -ne 0 ]; then
    echo "ERROR: Recording failed"
    exit 1
fi

# Step 2: Show recording info
echo "=== Step 2: Recording information ==="
python3 src/recording/record_replay_logs.py info --file "$RECORDING_FILE"

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to get recording info"
    exit 1
fi

# Step 3: Wait before replay
echo "=== Step 3: Preparing for replay ==="
echo "Waiting 3 seconds before replay..."
sleep 3

# Step 4: Replay and capture
echo "=== Step 4: Replaying and capturing ==="
python3 src/playback/replay_with_sensors.py $REPLAY_MODE --file "$RECORDING_FILE" --output "$OUTPUT_DIR" --duration $RECORDING_DURATION --sync

if [ $? -ne 0 ]; then
    echo "ERROR: Replay and capture failed"
    exit 1
fi

echo "=== CARLA Internal Pipeline Completed Successfully ==="
echo "Recording saved to: $RECORDING_FILE"
echo "Output saved to: $OUTPUT_DIR" 