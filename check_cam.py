import cv2
import numpy as np

cap0 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(2)


r, f = cap0.read()
if r:
    np.save("/tmp/cam0.npy", f)
    #cv2.imwrite("/tmp/cam0.png", f)

r, f = cap2.read()
if r:
    np.save("/tmp/cam2.npy", f)
