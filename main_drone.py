import os
import sys
import time  # datetime
import numpy as np
import cv2

import board
import busio
# import synscan
# from sscan1 import Sscan


from adafruit_bno08x import (
            BNO_REPORT_ACCELEROMETER,
            # BNO_REPORT_GYROSCOPE,
            BNO_REPORT_MAGNETOMETER,
            BNO_REPORT_ROTATION_VECTOR,
            # BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR,
)
from adafruit_bno08x.i2c import BNO08X_I2C

i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
bno.enable_feature(BNO_REPORT_MAGNETOMETER)
bno.enable_feature(BNO_REPORT_ACCELEROMETER)

# smc = synscan.motors()
# smc = Sscan('/dev/ttyUSB0', 9600, 0.2)
# smc.goto(0,0, True) # wait unitl the goto 0 0

cap = cv2.VideoCapture()
cap.open(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

ddir = input('data dir: ')
# ddir = "/mnt/storage/{}".format(
#    # '{0:%Y-%m-%d-%H}h'.format(datetime.datetime.now()))
if os.path.isdir(ddir):
    pass
    # Previous following peice was to manual
    if 'y' != input('dir is already exists, continue? y/n'):
        sys.exit()
else:
    os.mkdir(ddir)
t0 = time.time()
ct0 = time.ctime()
os.system("echo \"{}\" >> {}/0000.time".format(ct0, ddir))


# 15000
dBuf_img = np.zeros((20000, 260, 160), dtype=np.uint8)
dBuf_ori = np.zeros((20000, 12))

# exposure
expovals = [1, 2, 5, 10, 20, 39, 78, 156, 312, 625, 1250, 2500]
expo_ind = 8


def exposure(inc) -> None:
    global expo_ind
    if inc == 0:
        return
    expo_ind += inc
    if expo_ind > 11:
        expo_ind = 11
        return
    if expo_ind < 0:
        expo_ind = 0
        return
    os.system(
        f'v4l2-ctl -d0 -c exposure_absolute={expovals[expo_ind]}')
    print(
        f'v4l2-ctl -d0 -c exposure_absolute={expovals[expo_ind]}')

    for _ in range(10):
        cap.grab()       # for syncing


# while 1: #this is the looping.
for epoch in range(100):
    dBuf_img[:, :, :] = 0
    dBuf_ori[:, :] = 0
    count = 0
    for i in range(10):
        cap.grab()       # for syncing
    try:
        while count < 20000:
            bno_qua = bno.quaternion
            bno_acc = bno.acceleration
            bno_mag = bno.magnetic

            ret, frame = cap.read()

            if ret:
                dBuf_img[count, :, :] = frame[55:315, 235:395, 0]  # 260 x 160

                if bno_qua is not None:
                    dBuf_ori[count, 0:4] = bno_qua
                if bno_acc is not None:
                    dBuf_ori[count, 4:7] = bno_acc
                if bno_mag is not None:
                    dBuf_ori[count, 7:10] = bno_mag

                dBuf_ori[count, 10] = time.time() - t0
                dBuf_ori[count, 11] = expo_ind
                # dBuf_ori[count, :] = [i, j, k, r,
                #                       acc_x, acc_y, acc_z,
                #                       mag_x, mag_y, mag_z,
                #                       time.time()-t0, expo_ind]
                count += 1
            if count % 50 == 0:
                print(f"| {count=:6d} | {dBuf_ori[count, :]}")

            if (count % 10 == 0) and (count > 0):   # pass #check exposure here
                m_gray = np.max(np.mean(
                    dBuf_img[count-10:count, :, 110:140], axis=2), axis=1)
                m_targ = np.max(np.mean(
                    dBuf_img[count-10:count, :, 10:75],   axis=2), axis=1)
                m_grtr = np.maximum(m_gray, m_targ)

                inc_expo = 0
                if np.sum(m_grtr > 230) > 7:
                    inc_expo -= 1
                if np.sum(m_grtr < 90) > 7:
                    inc_expo += 1

                print(m_grtr.astype(np.uint8))
                exposure(inc_expo)

    except KeyboardInterrupt:
        print("Saving measurement wait for a while.", count)
        np.save(
            f'{ddir}/img_el0_{epoch:02d}_{count:04d}',
            dBuf_img[:count, :, :])
        np.save(
            f'{ddir}/ori_el__{epoch:02d}_{count:04d}',
            dBuf_ori[:count, :])
        print("Finished")
        sys.exit()

    np.save('{}/img_el0_{:02d}'.format(ddir, epoch), dBuf_img)
    np.save('{}/ori_el__{:02d}'.format(ddir, epoch), dBuf_ori)
