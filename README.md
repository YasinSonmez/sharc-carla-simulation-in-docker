# CARLA Simulation Pipeline in Docker

Automated CARLA simulation recording and playback pipeline designed for headless environments using Docker/Apptainer containers.

## Overview

This project provides a complete pipeline for:
- Recording CARLA simulations to log files
- Replaying simulations from logs and capturing frames
- Generating videos from captured frames

## Project Structure

```
sharc-carla-simulation-in-docker/
├── src/
│   ├── recording/          # Recording scripts
│   │   ├── record_images.py       # Direct camera recording
│   │   └── record_replay_logs.py  # CARLA log file recording
│   ├── playback/           # Playback and capture scripts
│   │   └── replay_with_sensors.py # Multi-mode replay with sensors
│   └── utils/              # Utility scripts
│       └── ffmpeg_video.py        # Video generation from frames
├── dockerfile              # CARLA 0.9.12 with dependencies
├── run_carla_pipeline.sh   # Main pipeline script
├── carla_internal_pipeline.sh # Internal container pipeline
└── data/                   # Output directories (auto-created)
    ├── recordings/         # CARLA log files (.log)
    ├── images/            # Captured image sequences
    └── videos/            # Generated video files
```

## Quick Start

### Option 1: Complete Automated Pipeline (Recommended)

Run the entire pipeline with a single command:

```bash
./run_carla_pipeline.sh
```

This will:
1. Start CARLA server in headless mode
2. Record a 30-second simulation
3. Replay and capture frames (follow mode)
4. Generate an MP4 video
5. Clean up automatically

### Option 2: Manual Step-by-Step

**1. Record a simulation:**
```bash
# Using Apptainer/Singularity
apptainer run --nv -e -B $PWD:/workspace carla912.sif python3 /workspace/src/recording/record_replay_logs.py record --duration 30 --file /workspace/data/recordings/my_recording.log

# Or directly with Python (requires CARLA server running)
cd src/recording
python record_replay_logs.py record --duration 30 --file ../../data/recordings/my_recording.log
```

**2. Replay and capture:**
```bash
cd src/playback
python replay_with_sensors.py follow --file ../../data/recordings/my_recording.log --output ../../data/images/follow --duration 30 --sync
```

**3. Generate video:**
```bash
cd src/utils
python ffmpeg_video.py
```

## Configuration

### Pipeline Script Configuration

Edit `run_carla_pipeline.sh` to customize:

```bash
CARLA_CONTAINER="carla912.sif"    # Container name
CARLA_PORT=2000                   # CARLA server port
RECORDING_DURATION=30             # Recording duration (seconds)
RECORDING_FILE="data/recordings/test.log"  # Output log file
OUTPUT_DIR="data/images/test"    # Image output directory
REPLAY_MODE="follow"              # Options: follow, camera, data
```

### Recording Modes

**Direct Image Recording:**
```bash
cd src/recording
python record_images.py  # Uses built-in configuration
```

**Log-based Recording:**
```bash
python record_replay_logs.py record --duration 20 --file ../../data/recordings/simulation.log
python record_replay_logs.py info --file ../../data/recordings/simulation.log  # View log details
```

## Docker Setup

### Building the Container

The `dockerfile` creates a CARLA 0.9.12 environment with:
- CARLA 0.9.12 base image
- Python 3.7 with required packages
- OpenCV, NumPy, Pandas, Matplotlib
- FFmpeg with H.264 support
- Scenario Runner integration


## Output Files

- **Log Files:** `.log` files containing complete simulation data
- **Images:** `frame_XXXXXX.jpg` sequences (800x600, 20 FPS)
- **Videos:** `.mp4` files with H.264 encoding
- **Data:** Vehicle position/velocity data in text format

## Troubleshooting

**CARLA Server Issues:**
- Ensure port 2000 is available
- Check NVIDIA driver compatibility
- Verify container has GPU access (`--nv` flag)