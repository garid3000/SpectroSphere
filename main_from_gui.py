import os
import time
import sys
from datetime import datetime
import numpy as np
import cv2

# import board
# import busio
# import synscan
from custom_libs.sscan1 import Sscan
import queue
import threading

import board
import busio
from adafruit_bno08x.i2c import BNO08X_I2C
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)




# ----------------------------------------------------------
class xVideoCapture:
    def __init__(self, name: str, fourcc: str = "MJPEG"):
        self.cap = cv2.VideoCapture()  # type: ignore
        self.cap.open(name, apiPreference=cv2.CAP_V4L2)
        if fourcc == "YUYV":
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "U", "Y", "V"))
        else:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_APERTURE, 1)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
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


class xOriSensor:
    def __init__(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)  # , frequency=100000)
        self.bno = BNO08X_I2C(self.i2c)
        self.bno.enable_feature(BNO_REPORT_ACCELEROMETER)
        self.bno.enable_feature(BNO_REPORT_GYROSCOPE)
        self.bno.enable_feature(BNO_REPORT_MAGNETOMETER)
        self.bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

        self.q_ori = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        quat_i, quat_j, quat_k, quat_real = 0, 0, 0, 0
        while True:
            try:
                quat_i, quat_j, quat_k, quat_real = self.bno.quaternion
            except Exception:
                quat_i, quat_j, quat_k, quat_real = 0, 1, 2, 3


            if not self.q_ori.empty():
                try:
                    self.q_ori.get_nowait()  # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q_ori.put((quat_i, quat_j, quat_k, quat_real))

    def read(self):
        return self.q_ori.get()



# ----------------------------------------------------------
cli_args = {each_arg.split("=")[0]: each_arg.split("=")[1] for each_arg in sys.argv[1:] if each_arg.count("=") == 1}

elv0 = int(cli_args["elv0"])
elv1 = int(cli_args["elv1"])
azi0 = int(cli_args["azi0"])
azi1 = int(cli_args["azi1"])

# ---------------------------------------------------------

# smc = synscan.motors()
smc = Sscan("/dev/ttyUSB0", 9600, 0.2)
smc.goto(0, 0, True)  # wait unitl the goto 0 0


cap0 = xVideoCapture("/dev/video0", fourcc="YUYV")
cap2 = xVideoCapture("/dev/video2", fourcc="MJPG")
snsr = xOriSensor()


dBuf_img0 = np.zeros((4000, 480, 640), dtype=np.uint8)
dBuf_img1 = np.zeros((4000, 480, 640), dtype=np.uint8)
dBuf_ori = np.zeros((4000, 7))


ddir = os.path.join(
    "/home/pi/",
    datetime.now().strftime("data_%Y%m%d_%H%M%S_") + cli_args["ddir"],
)
os.makedirs(ddir, exist_ok=True)

t0 = time.time()
ct0 = time.ctime()
os.system('echo "{}" >> {}/0000.time'.format(ct0, ddir))

#######################################################################################################################
for el in range(elv0, elv1, 10):
    smc.goto(azi0, el, True)
    dBuf_img0[:, :, :] = 0
    dBuf_img1[:, :, :] = 0
    dBuf_ori[:, :] = 0
    count = 0
    time.sleep(0.5)
    smc.goto(azi1, el, False)

    while 1:
        i, j, k, r = snsr.read() #0, 0, 0, 0  # bno.quaternion      # orientation
        frame = cap0.read()  # spectrum
        curazi = smc.get_pos_deg(1)  # orientation from motors
        print(count, el, "%.2f" % curazi, time.time() - t0, i, j, k, r)
        dBuf_img0[count, :, :] = cap0.read()[:, :, 0]  # frame[:, :, 0]
        dBuf_img1[count, :, :] = cap2.read()[:, :, 0]  # frame[:, :, 0] #dBuf_img1[count,:,:] = frame1[:, 200:400, 0].reshape(200,480)
        dBuf_ori[count, :] = [el, curazi, i, j, k, r, time.time() - t0]
        count += 1

        if abs(curazi - azi1) < 0.2:
            break
    np.save("{}/img_el0_{:3.1f}".format(ddir, el), dBuf_img0[:count, :, :])
    np.save("{}/img_el2_{:3.1f}".format(ddir, el), dBuf_img1[:count, :, :])
    np.save("{}/ori_el__{:3.1f}".format(ddir, el), dBuf_ori[:count, :])

    smc.goto(azi1, el + 5, True)
    dBuf_img0[:, :, :] = 0
    dBuf_img1[:, :, :] = 0
    dBuf_ori[:, :] = 0
    count = 0
    time.sleep(0.5)
    smc.goto(azi0, el + 5, False)
    while 1:
        i, j, k, r = 0, 0, 0, 0  # bno.quaternion      # orientation
        curazi = smc.get_pos_deg(1)  # orientation from motors
        print(count, el + 5, "%.2f" % curazi, time.time() - t0)
        dBuf_img0[count, :, :] = cap0.read()[:, :, 0]  # frame[:, 200:400, 0].reshape(200,480)
        dBuf_img1[count, :, :] = cap2.read()[:, :, 0]  # frame1[:, 200:400, 0].reshape(200,480)
        dBuf_ori[count, :] = [el + 5, curazi, i, j, k, r, time.time() - t0]
        count += 1

        if abs(curazi - azi0) < 0.2:
            break

    np.save("{}/img_el0_{:3.1f}".format(ddir, el + 5), dBuf_img0[:count, :, :])
    np.save("{}/img_el2_{:3.1f}".format(ddir, el + 5), dBuf_img1[:count, :, :])
    np.save("{}/ori_el__{:3.1f}".format(ddir, el + 5), dBuf_ori[:count, :])
