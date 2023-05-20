import time
import numpy as np
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

try:
    while 1:
        ret, frame = cap.read()
        if ret:
            segment = frame[:,250:280,0]
            spectra = np.mean(segment, axis = 1)
            segment = frame[:,350:380,0]
            spectra1 = np.mean(segment, axis = 1)
            print(chr(12))
            for i in range(0,480, 10):
                x = int(np.mean(spectra[i:i+10])) // 3
                y = int(np.mean(spectra1[i:i+10])) // 3
                print('#' * x + ' ' * (90-x) + '#' * y)
            time.sleep(.6)


except KeyboardInterrupt:
    cv2.imwrite('/home/pi/2c.png', frame)
    pass

cap.release()
