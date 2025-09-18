#!/bin/bash

# === Configuration Parameters ===
CARLA_CONTAINER="carla912.sif"
CARLA_PORT=2000
RECORDING_DURATION=30
RECORDING_FILE="data/recordings/test.log"
OUTPUT_DIR="data/images/test"
REPLAY_MODE="follow"  # Options: follow, camera, data

module load ffmpeg
# Create necessary directories
mkdir -p "$(dirname "$RECORDING_FILE")"
mkdir -p "$OUTPUT_DIR"
mkdir -p "data/videos"

# Function to check if a process is running on a port
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Kill any existing processes on CARLA port
if check_port $CARLA_PORT; then
    echo "Killing existing process on port $CARLA_PORT"
    fuser -k $CARLA_PORT/tcp
    sleep 2
fi

echo "=== Starting CARLA Pipeline ==="
echo "Container: $CARLA_CONTAINER"
echo "Port: $CARLA_PORT"
echo "Duration: $RECORDING_DURATION seconds"
echo "Recording: $RECORDING_FILE"
echo "Output: $OUTPUT_DIR"
echo "Mode: $REPLAY_MODE"

# Run the entire pipeline inside a single apptainer instance
echo "Launching CARLA container..."
apptainer run --nv -e $CARLA_CONTAINER ./carla_internal_pipeline.sh $CARLA_PORT $RECORDING_DURATION "$RECORDING_FILE" "$OUTPUT_DIR" $REPLAY_MODE

PIPELINE_EXIT_CODE=$?

# Final cleanup - kill any remaining processes on the port (just in case)
if check_port $CARLA_PORT; then
    echo "Final cleanup: killing any remaining processes on port $CARLA_PORT..."
    fuser -k $CARLA_PORT/tcp 2>/dev/null || true
fi

if [ $PIPELINE_EXIT_CODE -eq 0 ]; then
    echo "=== Pipeline completed successfully! ==="
    echo "Recording saved to: $RECORDING_FILE"
    echo "Output saved to: $OUTPUT_DIR"
    
    # Step 5: Generate video from captured frames
    echo "=== Step 5: Generating video ==="
    
    # Check if we have captured frames
    if [ -d "$OUTPUT_DIR" ] && [ "$(ls -A $OUTPUT_DIR 2>/dev/null)" ]; then
        FRAME_COUNT=$(ls -1 $OUTPUT_DIR/*.jpg 2>/dev/null | wc -l)
        if [ $FRAME_COUNT -gt 0 ]; then
            echo "Found $FRAME_COUNT frames, creating video..."
            
            # Create videos directory
            VIDEO_DIR="data/videos"
            mkdir -p "$VIDEO_DIR"
            
            # Generate video filename based on recording and mode
            RECORDING_NAME=$(basename "$RECORDING_FILE" .log)
            VIDEO_FILE="$VIDEO_DIR/${RECORDING_NAME}_${REPLAY_MODE}.mp4"
            
            # Use ffmpeg to create video
            if command -v ffmpeg >/dev/null 2>&1; then
                echo "Checking ffmpeg codec support..."
                
                # All replay modes now use the same frame naming pattern
                FRAME_PATTERN="$OUTPUT_DIR/frame_%06d.jpg"
                
                # Check for codec support and choose best available option
                if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q "libx264"; then
                    echo "Using H.264 codec with good quality settings"
                    CODEC_ARGS="-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p"
                elif ffmpeg -hide_banner -encoders 2>/dev/null | grep -q "mpeg4"; then
                    echo "Using MPEG-4 codec (libx264 not available)"
                    CODEC_ARGS="-c:v mpeg4 -b:v 8M"
                else
                    echo "Using default codec with high bitrate"
                    CODEC_ARGS="-b:v 10M"
                fi
                
                echo "Creating video: $VIDEO_FILE"
                ffmpeg -y -framerate 20 -i "$FRAME_PATTERN" $CODEC_ARGS -r 20 "$VIDEO_FILE" -loglevel error
                
                if [ $? -eq 0 ] && [ -f "$VIDEO_FILE" ]; then
                    VIDEO_SIZE=$(du -h "$VIDEO_FILE" | cut -f1)
                    echo "✅ Video created successfully: $VIDEO_FILE ($VIDEO_SIZE)"
                else
                    echo "❌ Failed to create video with current codec, trying basic settings..."
                    # Fallback to most basic ffmpeg settings
                    ffmpeg -y -framerate 20 -i "$FRAME_PATTERN" -r 20 "$VIDEO_FILE" -loglevel error
                    if [ $? -eq 0 ] && [ -f "$VIDEO_FILE" ]; then
                        VIDEO_SIZE=$(du -h "$VIDEO_FILE" | cut -f1)
                        echo "✅ Video created with basic settings: $VIDEO_FILE ($VIDEO_SIZE)"
                    else
                        echo "❌ Failed to create video with all attempted settings"
                    fi
                fi
            else
                echo "⚠️  ffmpeg not found. Installing ffmpeg is recommended for video generation."
                echo "   You can manually create videos using: python3 src/utils/ffmpeg_video.py"
            fi
        else
            echo "⚠️  No image frames found in $OUTPUT_DIR"
        fi
    else
        echo "⚠️  Output directory $OUTPUT_DIR is empty or doesn't exist"
    fi
    
    echo "=== Final Summary ==="
    echo "📁 Recording: $RECORDING_FILE"
    echo "📁 Images: $OUTPUT_DIR ($FRAME_COUNT frames)"
    if [ -f "$VIDEO_FILE" ]; then
        echo "🎬 Video: $VIDEO_FILE"
    fi
    echo "=== All done! ==="
else
    echo "=== Pipeline failed with exit code $PIPELINE_EXIT_CODE ==="
    exit $PIPELINE_EXIT_CODE
fi 