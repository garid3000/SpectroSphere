import numpy as np
import cv2

vid = cv2.VideoCapture("/mnt/usb/output_lossless_ffv1.avi")
arr = np.load("/mnt/usb/frames_array.npy")

if not vid.isOpened():
    print("Error: Could not open video.")
    exit()

frame_count = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
assert frame_count == arr.shape[0]


num_pixel_with_different_values = 0
for i in range(frame_count):
    # Read a frame from the video
    ret, frame_from_vid = vid.read()
    frame_from_arr = arr[i, :, :, :]


    diff_in_this_ith_frame = np.sum(np.abs(frame_from_arr - frame_from_vid))
    num_pixel_with_different_values += diff_in_this_ith_frame
    print(f"{i} of {frame_count}: \t diff:{diff_in_this_ith_frame} total-error:{num_pixel_with_different_values} \t {frame_from_vid.shape=}")

    if not ret:
        break  # Exit the loop if there are no more frames

    hconcat_image = cv2.hconcat([frame_from_vid, frame_from_arr, frame_from_vid - frame_from_arr])
    cv2.imshow("Video Frame", hconcat_image)

    if cv2.waitKey(15) & 0xFF == ord("q"):
        break

vid.release()
cv2.destroyAllWindows()
