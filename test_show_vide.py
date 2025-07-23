import numpy as np
import cv2
from curses.ascii import isprint


vid = cv2.VideoCapture("/tmp/20250723-193459.avi")

if not vid.isOpened():
    print("Error: Could not open video.")
    exit()

frame_count = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))


num_pixel_with_different_values = 0
for i in range(frame_count):
    # Read a frame from the video
    ret, frame_from_vid = vid.read()
    #frame_from_arr = arr[i, :, :, :]


    #diff_in_this_ith_frame = np.sum(np.abs(frame_from_arr - frame_from_vid))
    #num_pixel_with_different_values += diff_in_this_ith_frame
    #print(f"{i} of {frame_count}: \t diff:{diff_in_this_ith_frame} total-error:{num_pixel_with_different_values} \t {frame_from_vid.shape=}")

    if not ret:
        break  # Exit the loop if there are no more frames

    hconcat_image = cv2.hconcat([ frame_from_vid ])
    #hconcat_image = cv2.hconcat([frame_from_vid, frame_from_arr, frame_from_vid - frame_from_arr])
    cv2.imshow("Video Frame", hconcat_image[:, :, ::-1])

    n = 0
    for i in range(1280):
        if not isprint( frame_from_vid[-1, i, 0]):
            n = i
            break


    last_line = frame_from_vid[-1, :n, 0].tobytes().decode()
    print(f"{i:05d} {n} {last_line[:n]}")

    if cv2.waitKey(150) & 0xFF == ord("q"):
        break

vid.release()
cv2.destroyAllWindows()
