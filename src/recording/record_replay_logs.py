import carla
import time
import os
import argparse

def record_log(client, world, duration=10, log_filename="recording.log"):
    """Record CARLA simulation to a log file"""
    # Ensure absolute path and create directory if needed
    log_filename = os.path.abspath(log_filename)
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)
    
    print(f"Starting recording for {duration} seconds...")
    print(f"Recording to: {log_filename}")
    print(f"Directory exists: {os.path.exists(os.path.dirname(log_filename))}")
    print(f"Directory writable: {os.access(os.path.dirname(log_filename), os.W_OK)}")
    
    # Check if file already exists
    if os.path.exists(log_filename):
        print(f"Warning: File {log_filename} already exists, will be overwritten")
    
    # Start recording
    print("Starting CARLA recorder...")
    try:
        client.start_recorder(log_filename)
        print("Recorder started successfully")
    except Exception as e:
        print(f"Error starting recorder: {e}")
        return
    
    # Spawn a vehicle for some activity
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]
    spawn_point = world.get_map().get_spawn_points()[0]
    vehicle = world.spawn_actor(vehicle_bp, spawn_point)
    vehicle.set_autopilot(True)
    print(f"Vehicle spawned with ID: {vehicle.id}")
    
    # Record for specified duration
    print(f"Recording for {duration} seconds...")
    for i in range(duration):
        time.sleep(1)
        print(f"Recording... {i+1}/{duration} seconds")
    
    # Stop recording - let CARLA handle vehicle cleanup
    print("Stopping recorder...")
    try:
        client.stop_recorder()
        print("Recorder stopped successfully")
    except Exception as e:
        print(f"Error stopping recorder: {e}")
    
    # Check if file was actually created
    if os.path.exists(log_filename):
        file_size = os.path.getsize(log_filename)
        print(f"Recording saved to {log_filename}")
        print(f"File size: {file_size} bytes")
        if file_size == 0:
            print("WARNING: File is empty!")
    else:
        print(f"ERROR: Recording file was not created at {log_filename}")
        # List directory contents to debug
        dir_path = os.path.dirname(log_filename)
        print(f"Directory contents of {dir_path}:")
        try:
            for item in os.listdir(dir_path):
                print(f"  - {item}")
        except Exception as e:
            print(f"  Error listing directory: {e}")
    
    # Don't destroy vehicle manually - this causes the runtime error
    # CARLA will clean up when the world reloads or client disconnects

def replay_log(client, log_filename="recording.log", start_time=0, duration=0, follow_id=0):
    """Replay a CARLA log file"""
    # Ensure absolute path
    log_filename = os.path.abspath(log_filename)
    
    print(f"Checking log file: {log_filename}")
    if not os.path.exists(log_filename):
        print(f"Log file {log_filename} not found!")
        return
    
    file_size = os.path.getsize(log_filename)
    print(f"File exists, size: {file_size} bytes")
    print(f"Replaying {log_filename}...")
    
    try:
        # Replay the log
        # duration=0 means replay entire log
        # follow_id=0 means no specific actor to follow
        client.replay_file(log_filename, start_time, duration, follow_id)
        print("Replay started. The simulation will run the recorded events.")
        
        # Wait for replay to finish or run for specified duration
        if duration > 0:
            print(f"Replay will run for {duration} seconds...")
            time.sleep(duration)
        else:
            # If no duration specified, run for a reasonable time
            # You can estimate based on original recording length
            print("Replay running... (press Ctrl+C to stop)")
            try:
                time.sleep(30)  # Default 30 seconds, adjust as needed
            except KeyboardInterrupt:
                print("\nReplay stopped by user")
        
        print("Replay completed.")
        
    except Exception as e:
        print(f"Error starting replay: {e}")
        print("This might be because the CARLA server cannot access the file path.")

def get_log_info(client, log_filename="recording.log"):
    """Get information about a recorded log"""
    # Ensure absolute path
    log_filename = os.path.abspath(log_filename)
    
    print(f"Checking log file: {log_filename}")
    if not os.path.exists(log_filename):
        print(f"Log file {log_filename} not found on filesystem!")
        return
    
    file_size = os.path.getsize(log_filename)
    print(f"File exists, size: {file_size} bytes")
    
    try:
        info = client.show_recorder_file_info(log_filename, True)
        print("Log file information:")
        print(info)
    except Exception as e:
        print(f"Error getting log info from CARLA server: {e}")
        print("This might be because the CARLA server cannot access the file path.")

def main():
    parser = argparse.ArgumentParser(description='CARLA Log Recorder/Replayer')
    parser.add_argument('action', choices=['record', 'replay', 'info'], 
                       help='Action to perform')
    parser.add_argument('--file', default='recording.log', 
                       help='Log filename (default: recording.log)')
    parser.add_argument('--duration', type=int, default=10, 
                       help='Duration in seconds for recording (default: 10)')
    parser.add_argument('--start', type=float, default=0, 
                       help='Start time for replay (default: 0)')
    parser.add_argument('--follow', type=int, default=0, 
                       help='Actor ID to follow during replay (default: 0)')
    
    args = parser.parse_args()
    
    # Connect to CARLA
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.load_world('Town03')
    
    if args.action == 'record':
        record_log(client, world, args.duration, args.file)
    elif args.action == 'replay':
        replay_log(client, args.file, args.start, args.duration, args.follow)
    elif args.action == 'info':
        get_log_info(client, args.file)

if __name__ == '__main__':
    main() 