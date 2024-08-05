
import os
import time
import sys
from datetime import datetime
import numpy as np
import cv2

from custom_libs.sscan1 import Sscan
import queue
import threading

# ----------------------------------------------------------
class xVideoCapture:
    def __init__(self, name: str, fourcc: str = "MJPEG", autoexpo=3, fps=15, frame_w=640, frame_h=480):
        self.cap = cv2.VideoCapture()  # type: ignore
        self.cap.open(name, apiPreference=cv2.CAP_V4L2)
        if fourcc == "YUYV":
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "U", "Y", "V"))
        else:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        #self.cap.set(cv2.CAP_PROP_APERTURE, 1)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, autoexpo)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_h)

        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()  # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return self.q.get()


# ----------------------------------------------------------
cli_args = {each_arg.split("=")[0]: each_arg.split("=")[1] for each_arg in sys.argv[1:] if each_arg.count("=") == 1}

duration = int(cli_args["time"])
batchsize = int(cli_args["batch"]) if "batch" in cli_args else 40000

# ---------------------------------------------------------

cap0 = xVideoCapture("/dev/video0", fourcc="YUYV", fps=30, autoexpo=1)
cap2 = xVideoCapture("/dev/video2", fourcc="MJPG", autoexpo=3, frame_w=320, frame_h=240)

ddir = os.path.join(
    "/home/pi/",
    datetime.now().strftime("data_%Y%m%d_%H%M%S_") + cli_args["ddir"],
)
os.makedirs(ddir, exist_ok=True)

dBuf_img0 = np.memmap(os.path.join(ddir, "spectr.mmmp.npy"), mode="r+", shape=(batchsize, 480, 200), dtype=np.uint8)
dBuf_img1 = np.memmap(os.path.join(ddir, "webcam.mmmp.npy"), mode="r+", shape=(batchsize, 240, 320), dtype=np.uint8)
dBuf_ori  = np.memmap(os.path.join(ddir, "orient.mmmp.npy"), mode="r+", shape=(batchsize, 7))

dBuf_img0[:] = 0
dBuf_img1[:] = 0
dBuf_ori[:] = 0

t0 = time.time()
ct0 = time.ctime()
os.system('echo "{}" >> {}/0000.time'.format(ct0, ddir))

#######################################################################################################################
count = 0
while (time.time() - t0 < duration):
    frame = cap0.read()
    dBuf_img0[count, :, :] = cap0.read()[:, 200:400, 0]
    dBuf_img1[count, :, :] = cap2.read()[:, :, 0]      
    dBuf_ori[count, -1] = time.time() - t0
    count += 1
