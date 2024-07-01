import cv2
import numpy as np

cap0 = cv2.VideoCapture(0)
r, f = cap0.read()
if r:
    np.save("/tmp/cam0.npy", f)
cap0.release()

cap2 = cv2.VideoCapture(2)
frame_0 = np.zeros(f.shape, f.dtype)
r, f = cap2.read()
if r:
    frame_0[:f.shape[0], :f.shape[1], :] = f[:, :, :]
    np.save("/tmp/cam2.npy", frame_0)
