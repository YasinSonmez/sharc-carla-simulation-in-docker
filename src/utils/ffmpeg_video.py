import os
import subprocess
import glob

# === CONFIG ===
SAVE_DIR = 'output_images'       # Same directory used by CARLA script
VIDEO_FILE = 'carla_output.mp4'  # Output video file name
FPS = 20                         # Match the FPS from CARLA script
BITRATE = '5M'                   # Video bitrate (higher = better quality)

def create_video():
    if not os.path.exists(SAVE_DIR):
        print(f"Directory {SAVE_DIR} does not exist.")
        return False

    # Check if we have image files
    image_pattern = os.path.join(SAVE_DIR, 'frame_*.jpg')
    image_files = glob.glob(image_pattern)
    
    if not image_files:
        print(f"No image files found in {SAVE_DIR}")
        return False
    
    print(f"Found {len(image_files)} images. Creating video...")

    # Basic ffmpeg command compatible with most installations
    cmd = [
        'ffmpeg', '-y',                    # Overwrite output file
        '-framerate', str(FPS),            # Input framerate
        '-i', os.path.join(SAVE_DIR, 'frame_%06d.jpg'),  # Input pattern
        '-b:v', BITRATE,                   # Video bitrate
        '-r', str(FPS),                    # Output framerate
        VIDEO_FILE
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Video created: {VIDEO_FILE}")
        
        # Show file size
        if os.path.exists(VIDEO_FILE):
            size_mb = os.path.getsize(VIDEO_FILE) / (1024 * 1024)
            print(f"📁 Video size: {size_mb:.1f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg failed with error code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ ffmpeg not found. Please install ffmpeg.")
        return False

def create_video_with_bitrate(bitrate='5M', output_name=None):
    """Create video with custom bitrate settings"""
    global BITRATE, VIDEO_FILE
    
    original_bitrate = BITRATE
    original_video = VIDEO_FILE
    
    BITRATE = bitrate
    if output_name:
        VIDEO_FILE = output_name
    
    success = create_video()
    
    # Restore original settings
    BITRATE = original_bitrate
    VIDEO_FILE = original_video
    
    return success

if __name__ == '__main__':
    print("Creating video with high bitrate settings...")
    success = create_video()
    
    if success:
        print("\n💡 Bitrate options:")
        print("   2M: Good quality, smaller file")
        print("   5M: High quality (current default)")
        print("   10M: Very high quality, larger file")
        print("\n💡 Usage: create_video_with_bitrate('10M', 'high_quality.mp4')")
