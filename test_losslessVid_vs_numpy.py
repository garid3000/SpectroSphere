import cv2
import numpy as np

cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Error: Could not open video capture.")
    exit()

fourcc = cv2.VideoWriter_fourcc(*"FFV1")
output_file = "/tmp/output_lossless_ffv1.avi"
fps = 30.0
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Create a VideoWriter object
out = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))

n = 1000
npArray = np.empty((n, frame_height, frame_width, 3), dtype=np.uint8)

for i in range(n):
    ret, frame = cap.read()
    print(f"{i:03d}")
    if not ret:
        print("Failed retrieval")
        continue

    npArray[i, :, :, :] = frame[:, :, :3]
    out.write(frame)

out.release()
cap.release()
np.save("/tmp/frames_array.npy", npArray)
