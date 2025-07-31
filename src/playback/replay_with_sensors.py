import carla
import time
import os
import argparse

# Configuration
CAMERA_SIZE = (800, 600)
FPS = 20  # Match recording FPS
SPECTATOR_POS = carla.Transform(carla.Location(x=50, y=0, z=30), carla.Rotation(pitch=-30))
FOLLOW_POS = carla.Transform(carla.Location(x=-8, z=6), carla.Rotation(pitch=-15))

def run_replay(client, log_file, capture_func, duration, sync_mode):
    """Start replay and run capture function for specified duration"""
    log_file = os.path.abspath(log_file)
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return
    
    print(f"Starting replay: {os.path.basename(log_file)}")
    
    # Setup world and mode settings
    world = client.get_world()
    settings = world.get_settings()
    original_settings = settings
    
    if sync_mode:
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 1.0 / FPS
        world.apply_settings(settings)
        print(f"Using SYNCHRONOUS mode - exact {int(duration * FPS)} frames")
    else:
        settings.synchronous_mode = False
        world.apply_settings(settings)
        print(f"Using ASYNCHRONOUS mode - {duration} seconds real-time")
    
    # Start replay
    client.replay_file(log_file, 0, 0, 0)
    
    # Give replay time to initialize and spawn actors
    print("Waiting for replay to initialize...")
    if sync_mode:
        # In sync mode, tick a few times to let actors spawn
        for _ in range(10):
            world.tick()
    else:
        # In async mode, wait a moment
        time.sleep(1.0)
    
    try:
        if sync_mode:
            # Synchronous mode - exact frame count
            target_frames = int(duration * FPS)
            capture_func(world, target_frames, sync_mode)
        else:
            # Asynchronous mode - time-based
            capture_func(world, duration, sync_mode)
    finally:
        # Restore original settings
        world.apply_settings(original_settings)

def create_camera(world, transform, sync_mode, attach_to=None):
    """Create camera with standard settings"""
    camera_bp = world.get_blueprint_library().find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', str(CAMERA_SIZE[0]))
    camera_bp.set_attribute('image_size_y', str(CAMERA_SIZE[1]))
    
    if sync_mode:
        camera_bp.set_attribute('sensor_tick', '0.0')  # Capture every tick in sync mode
    else:
        camera_bp.set_attribute('sensor_tick', str(1.0 / FPS))  # Time-based capture
    
    return world.spawn_actor(camera_bp, transform, attach_to=attach_to)

def camera_mode(client, log_file, output_dir, duration, sync_mode):
    """Capture spectator camera images"""
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    frame_count = 0
    camera = None
    captured_image = None
    start_time = None
    
    def capture_frames(world, target, sync_mode):
        nonlocal camera, frame_count, captured_image, start_time
        camera = create_camera(world, SPECTATOR_POS, sync_mode)
        start_time = time.time()
        
        if sync_mode:
            def on_image(image):
                nonlocal captured_image
                captured_image = image
            
            camera.listen(on_image)
            print(f"Capturing {target} frames at {FPS} FPS to: {output_dir}")
            
            while frame_count < target:
                world.tick()
                if captured_image is not None:
                    filename = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
                    captured_image.save_to_disk(filename, carla.ColorConverter.Raw)
                    frame_count += 1
                    captured_image = None
                    if frame_count % 20 == 0:
                        print(f"Captured {frame_count}/{target} frames")
        else:
            def save_image(image):
                nonlocal frame_count
                filename = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
                image.save_to_disk(filename, carla.ColorConverter.Raw)
                frame_count += 1
                if frame_count % 20 == 0:
                    elapsed = time.time() - start_time
                    fps_actual = frame_count / elapsed if elapsed > 0 else 0
                    print(f"Recording... {elapsed:.1f}s elapsed, {frame_count} frames ({fps_actual:.1f} FPS)")
            
            camera.listen(save_image)
            print(f"Recording for {target} seconds to: {output_dir}")
            while time.time() - start_time < target:
                time.sleep(0.1)  # Small sleep to prevent busy waiting
    
    try:
        run_replay(client, log_file, capture_frames, duration, sync_mode)
    finally:
        if camera:
            camera.destroy()
    
    elapsed = time.time() - start_time if start_time else 0
    fps_actual = frame_count / elapsed if elapsed > 0 else 0
    print(f"Captured {frame_count} frames ({fps_actual:.1f} FPS average)")

def data_mode(client, log_file, duration, output_dir, sync_mode):
    """Extract vehicle data"""
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "vehicle_data.txt")
    frame_count = 0
    start_time = None
    
    def extract_data(world, target, sync_mode):
        nonlocal frame_count, start_time
        start_time = time.time()
        
        # Wait for vehicles to spawn from replay
        print("Waiting for vehicles to spawn from replay...")
        vehicles = []
        wait_attempts = 0
        max_wait_attempts = 50  # 5 seconds at 0.1s intervals
        
        while not vehicles and wait_attempts < max_wait_attempts:
            if sync_mode:
                world.tick()  # In sync mode, tick to advance simulation
            else:
                time.sleep(0.1)  # In async mode, just wait
            vehicles = world.get_actors().filter('vehicle.*')
            wait_attempts += 1
            if wait_attempts % 10 == 0:
                print(f"Still waiting for vehicles... ({wait_attempts/10:.1f}s)")
        
        if not vehicles:
            print("No vehicles found after waiting 5 seconds")
            return
        
        print(f"Found {len(vehicles)} vehicle(s) to track")
        
        with open(output_file, 'w') as f:
            if sync_mode:
                print(f"Extracting vehicle data for {target} frames...")
                while frame_count < target:
                    world.tick()
                    vehicles = world.get_actors().filter('vehicle.*')
                    
                    f.write(f"\n--- Frame {frame_count} ---\n")
                    for vehicle in vehicles:
                        try:
                            t = vehicle.get_transform()
                            v = vehicle.get_velocity()
                            f.write(f"Vehicle {vehicle.id}: pos=({t.location.x:.1f},{t.location.y:.1f}) vel=({v.x:.1f},{v.y:.1f})\n")
                        except:
                            pass
                    
                    frame_count += 1
                    if frame_count % 20 == 0:
                        print(f"Processed {frame_count}/{target} frames")
            else:
                print(f"Extracting vehicle data for {target} seconds...")
                while time.time() - start_time < target:
                    vehicles = world.get_actors().filter('vehicle.*')
                    
                    f.write(f"\n--- Frame {frame_count} ---\n")
                    for vehicle in vehicles:
                        try:
                            t = vehicle.get_transform()
                            v = vehicle.get_velocity()
                            f.write(f"Vehicle {vehicle.id}: pos=({t.location.x:.1f},{t.location.y:.1f}) vel=({v.x:.1f},{v.y:.1f})\n")
                        except:
                            pass
                    
                    frame_count += 1
                    if frame_count % 20 == 0:
                        elapsed = time.time() - start_time
                        fps_actual = frame_count / elapsed if elapsed > 0 else 0
                        print(f"Recording... {elapsed:.1f}s elapsed, {frame_count} frames ({fps_actual:.1f} FPS)")
                    time.sleep(1.0 / FPS)  # Control capture rate
    
    run_replay(client, log_file, extract_data, duration, sync_mode)
    
    elapsed = time.time() - start_time if start_time else 0
    fps_actual = frame_count / elapsed if elapsed > 0 else 0
    print(f"Processed {frame_count} frames ({fps_actual:.1f} FPS average)")
    print(f"Vehicle data saved to: {output_file}")

def follow_mode(client, log_file, duration, output_dir, sync_mode):
    """Follow vehicle with camera"""
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    frame_count = 0
    camera = None
    captured_image = None
    start_time = None
    
    def follow_vehicle(world, target, sync_mode):
        nonlocal camera, frame_count, captured_image, start_time
        
        # Wait for vehicles to spawn from replay
        print("Waiting for vehicles to spawn from replay...")
        vehicles = []
        wait_attempts = 0
        max_wait_attempts = 50  # 5 seconds at 0.1s intervals
        
        while not vehicles and wait_attempts < max_wait_attempts:
            if sync_mode:
                world.tick()  # In sync mode, tick to advance simulation
            else:
                time.sleep(0.1)  # In async mode, just wait
            vehicles = world.get_actors().filter('vehicle.*')
            wait_attempts += 1
            if wait_attempts % 10 == 0:
                print(f"Still waiting for vehicles... ({wait_attempts/10:.1f}s)")
        
        if not vehicles:
            print("No vehicles found after waiting 5 seconds")
            return
        
        target_vehicle = vehicles[0]
        camera = create_camera(world, FOLLOW_POS, sync_mode, attach_to=target_vehicle)
        start_time = time.time()
        
        if sync_mode:
            def on_image(image):
                nonlocal captured_image
                captured_image = image
            
            camera.listen(on_image)
            print(f"Following vehicle {target_vehicle.id}, capturing {target} frames at {FPS} FPS to: {output_dir}")
            
            while frame_count < target:
                world.tick()
                if captured_image is not None:
                    filename = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
                    captured_image.save_to_disk(filename, carla.ColorConverter.Raw)
                    frame_count += 1
                    captured_image = None
                    if frame_count % 20 == 0:
                        print(f"Captured {frame_count}/{target} frames")
        else:
            def save_image(image):
                nonlocal frame_count
                filename = os.path.join(output_dir, f"frame_{frame_count:06d}.jpg")
                image.save_to_disk(filename, carla.ColorConverter.Raw)
                frame_count += 1
                if frame_count % 20 == 0:
                    elapsed = time.time() - start_time
                    fps_actual = frame_count / elapsed if elapsed > 0 else 0
                    print(f"Recording... {elapsed:.1f}s elapsed, {frame_count} frames ({fps_actual:.1f} FPS)")
            
            camera.listen(save_image)
            print(f"Following vehicle {target_vehicle.id} for {target} seconds to: {output_dir}")
            while time.time() - start_time < target:
                time.sleep(0.1)  # Small sleep to prevent busy waiting
    
    try:
        run_replay(client, log_file, follow_vehicle, duration, sync_mode)
    finally:
        if camera:
            camera.destroy()
    
    elapsed = time.time() - start_time if start_time else 0
    fps_actual = frame_count / elapsed if elapsed > 0 else 0
    print(f"Captured {frame_count} frames ({fps_actual:.1f} FPS average)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['camera', 'data', 'follow'])
    parser.add_argument('--file', default='recording.log')
    parser.add_argument('--output', default='replay_output', help='Output directory for all modes')
    parser.add_argument('--duration', type=float, required=True, help='Duration of replay in seconds')
    parser.add_argument('--sync', action='store_true', help='Use synchronous mode for exact frame control')
    args = parser.parse_args()
    
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    
    if args.mode == 'camera':
        camera_mode(client, args.file, args.output, args.duration, args.sync)
    elif args.mode == 'data':
        data_mode(client, args.file, args.duration, args.output, args.sync)
    elif args.mode == 'follow':
        follow_mode(client, args.file, args.duration, args.output, args.sync)

if __name__ == '__main__':
    main() 