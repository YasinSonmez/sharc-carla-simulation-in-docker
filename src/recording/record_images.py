import carla
import time
import os

# === CONFIG ===
SAVE_DIR = 'output_images'
RECORD_TIME = 5  # seconds
FPS = 20
SYNCHRONOUS_MODE = True  # True = exact frame count, False = real-time performance

def main():
    # Connect to CARLA
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.load_world('Town03')
    
    # Store original settings
    original_settings = world.get_settings()
    
    if SYNCHRONOUS_MODE:
        # Set synchronous mode for exact frame control
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 1.0 / FPS
        world.apply_settings(settings)
        print(f"Using SYNCHRONOUS mode - exact {RECORD_TIME * FPS} frames")
    else:
        # Use asynchronous mode for real-time performance
        settings = world.get_settings()
        settings.synchronous_mode = False
        world.apply_settings(settings)
        print(f"Using ASYNCHRONOUS mode - {RECORD_TIME} seconds real-time")
    
    # Spawn vehicle and camera
    blueprint_library = world.get_blueprint_library()
    vehicle = world.spawn_actor(
        blueprint_library.filter('vehicle.tesla.model3')[0],
        world.get_map().get_spawn_points()[0]
    )
    
    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '800')
    camera_bp.set_attribute('image_size_y', '600')
    
    if SYNCHRONOUS_MODE:
        camera_bp.set_attribute('sensor_tick', '0.0')  # Capture every tick
    else:
        camera_bp.set_attribute('sensor_tick', str(1.0 / FPS))  # Time-based capture
    
    camera = world.spawn_actor(
        camera_bp, 
        carla.Transform(carla.Location(x=1.5, z=2.4)), 
        attach_to=vehicle
    )
    
    # Setup recording
    os.makedirs(SAVE_DIR, exist_ok=True)
    frame_count = 0
    captured_image = None
    
    def save_image(image):
        nonlocal captured_image, frame_count
        if SYNCHRONOUS_MODE:
            captured_image = image
        else:
            # Save immediately in async mode
            filename = os.path.join(SAVE_DIR, f"frame_{frame_count:06d}.jpg")
            image.save_to_disk(filename, carla.ColorConverter.Raw)
            frame_count += 1
            if frame_count % 20 == 0:
                print(f"Captured {frame_count} frames")
    
    camera.listen(save_image)
    vehicle.set_autopilot(True)
    
    if SYNCHRONOUS_MODE:
        # Synchronous recording - exact frame count
        target_frames = RECORD_TIME * FPS
        print(f"Recording {target_frames} frames...")
        
        while frame_count < target_frames:
            world.tick()
            if captured_image is not None:
                filename = os.path.join(SAVE_DIR, f"frame_{frame_count:06d}.jpg")
                captured_image.save_to_disk(filename, carla.ColorConverter.Raw)
                frame_count += 1
                captured_image = None
                if frame_count % 20 == 0:
                    print(f"Captured {frame_count}/{target_frames} frames")
    else:
        # Asynchronous recording - time-based
        print(f"Recording for {RECORD_TIME} seconds...")
        start_time = time.time()
        
        while time.time() - start_time < RECORD_TIME:
            time.sleep(0.1)  # Small sleep to prevent busy waiting
            if frame_count > 0 and frame_count % 20 == 0:
                elapsed = time.time() - start_time
                fps_actual = frame_count / elapsed if elapsed > 0 else 0
                print(f"Recording... {elapsed:.1f}s elapsed, {frame_count} frames ({fps_actual:.1f} FPS)")
    
    print(f"Recording completed. {frame_count} frames saved.")
    
    # Cleanup
    camera.stop()
    camera.destroy()
    vehicle.destroy()
    
    # Restore original settings
    world.apply_settings(original_settings)

if __name__ == '__main__':
    main()
