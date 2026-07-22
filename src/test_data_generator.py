import cv2
import numpy as np

def generate_synthetic_crowd_video(output_path: str = "sample_crowd.mp4", duration_sec: int = 15, fps: int = 20, width: int = 640, height: int = 480):
    """
    Generates a synthetic crowd video featuring moving human figures
    with converging trajectories towards a central chokepoint to test detection,
    tracking, optical flow, divergence, and advection prediction.
    """
    print(f"[TestGen] Generating synthetic crowd video '{output_path}' ({duration_sec}s @ {fps} FPS)...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    num_frames = duration_sec * fps
    num_people = 12

    np.random.seed(42)
    positions = np.zeros((num_people, 2), dtype=np.float32)
    velocities = np.zeros((num_people, 2), dtype=np.float32)
    colors = []

    for i in range(num_people):
        angle = np.random.uniform(0, 2 * np.pi)
        radius = np.random.uniform(160, 230)
        positions[i, 0] = width / 2.0 + radius * np.cos(angle)
        positions[i, 1] = height / 2.0 + radius * np.sin(angle)
        
        speed = np.random.uniform(1.8, 3.2)
        velocities[i, 0] = -np.cos(angle) * speed
        velocities[i, 1] = -np.sin(angle) * speed
        
        # Shirt color (BGR)
        colors.append((int(np.random.randint(50, 220)), int(np.random.randint(50, 220)), int(np.random.randint(50, 220))))

    for frame_idx in range(num_frames):
        # Draw background (pavement ground)
        frame = np.full((height, width, 3), (215, 215, 215), dtype=np.uint8)

        # Draw ground grid lines
        for x in range(0, width, 50):
            cv2.line(frame, (x, 0), (x, height), (195, 195, 195), 1)
        for y in range(0, height, 50):
            cv2.line(frame, (0, y), (width, y), (195, 195, 195), 1)

        # Draw central chokepoint / gate
        cv2.circle(frame, (width//2, height//2), 35, (180, 180, 250), 2)

        # Update positions
        positions += velocities

        # Reverse direction when converging near chokepoint center
        for i in range(num_people):
            dist_to_center = np.hypot(positions[i, 0] - width/2, positions[i, 1] - height/2)
            if dist_to_center < 30:
                velocities[i] *= -1

            cx, cy = int(positions[i, 0]), int(positions[i, 1])
            shirt_color = colors[i]

            # Draw human figure (Torso, Head, Legs, Arms)
            # Legs
            cv2.line(frame, (cx - 4, cy + 15), (cx - 7, cy + 35), (40, 40, 40), 3)
            cv2.line(frame, (cx + 4, cy + 15), (cx + 7, cy + 35), (40, 40, 40), 3)
            # Torso (Shirt)
            cv2.rectangle(frame, (cx - 10, cy - 10), (cx + 10, cy + 15), shirt_color, -1)
            # Head
            cv2.circle(frame, (cx, cy - 18), 8, (170, 200, 230), -1)
            # Arms
            cv2.line(frame, (cx - 10, cy - 5), (cx - 16, cy + 10), shirt_color, 3)
            cv2.line(frame, (cx + 10, cy - 5), (cx + 16, cy + 10), shirt_color, 3)

        out.write(frame)

    out.release()
    print(f"[TestGen] Video successfully created: '{output_path}'.")

if __name__ == "__main__":
    generate_synthetic_crowd_video()
