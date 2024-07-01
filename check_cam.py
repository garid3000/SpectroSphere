import cv2
import numpy as np

cap0 = cv2.VideoCapture(0)
r, f = cap0.read()
if r:
    np.save("/tmp/cam0.npy", f)
cap0.release()

cap2 = cv2.VideoCapture(2)
r, f = cap2.read()
if r:
    np.save("/tmp/cam2.npy", f)
