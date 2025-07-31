# CARLA Docker Scripts

Organized scripts for recording and playing back CARLA simulations in headless environments.

## Folder Structure

```
carla_docker/
├── src/
│   ├── recording/          # Scripts for recording data
│   │   ├── record_images.py       # Record camera images directly
│   │   └── record_replay_logs.py  # Record/manage CARLA log files
│   ├── playback/           # Scripts for replaying recordings
│   │   └── replay_with_sensors.py # Replay logs with visual/data extraction
│   └── utils/              # Utility scripts
│       └── ffmpeg_video.py        # Convert image sequences to videos
├── data/                   # Output data storage
│   ├── recordings/         # CARLA log files (.log)
│   ├── images/            # Captured image sequences
│   └── videos/            # Generated video files
└── dockerfile              # Docker configuration
```

## Quick Start

### 1. Record a simulation log

**With Apptainer/Singularity:**
```bash
apptainer run --nv -e -B $PWD:/workspace carla915.sif python3 /workspace/src/recording/record_replay_logs.py record --duration 30 --file /workspace/data/recordings/my_recording.log
```

**Direct Python:**
```bash
cd src/recording
python record_replay_logs.py record --duration 30 --file ../../data/recordings/my_recording.log
```

### 2. Replay and capture visuals
```bash
cd ../playback
python replay_with_sensors.py camera --file ../../data/recordings/my_recording.log --output ../../data/images/replay_frames
```

### 3. Create video from images
```bash
cd ../utils
python ffmpeg_video.py
```

## Recording Options

**Direct image recording:**
```bash
cd src/recording
python record_images.py  # Uses config in file
```

**Log-based recording:**
```bash
python record_replay_logs.py record --duration 20 --file ../../data/recordings/simulation.log
python record_replay_logs.py info --file ../../data/recordings/simulation.log  # View log info
```

## Playback Options

**Spectator camera view:**
```bash
cd src/playback
python replay_with_sensors.py camera --file ../../data/recordings/recording.log --output ../../data/images/spectator
```

**Vehicle data extraction:**
```bash
python replay_with_sensors.py data --file ../../data/recordings/recording.log
```

**Follow vehicle camera:**
```bash
python replay_with_sensors.py follow --file ../../data/recordings/recording.log
```

## Requirements

- CARLA server running on localhost:2000
- Python with carla, opencv-python packages
- FFmpeg for video creation (optional) 