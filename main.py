import os
import time         # import datetime
import numpy as np
import cv2

# import board
# import busio
# from sscan1 import Sscan  # import synscan
from custom_libs.sscan1 import Sscan


# from adafruit_bno08x import (
#            BNO_REPORT_ACCELEROMETER,
#            BNO_REPORT_GYROSCOPE,
#            BNO_REPORT_MAGNETOMETER,
#            BNO_REPORT_ROTATION_VECTOR,
#            BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR,
# )
# from adafruit_bno08x.i2c import BNO08X_I2C

# i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
# bno = BNO08X_I2C(i2c)
# bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
# bno.enable_feature(BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR)


smc = Sscan('/dev/ttyUSB0', 9600, 0.2)
smc.goto(0, 0, wait=True)


cap = cv2.VideoCapture()
cap.open(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

dBuf_img = np.zeros((4000, 200, 480), dtype=np.uint8)
# dBuf_img1 = np.zeros((4000, 200, 480), dtype='uint8')
dBuf_ori = np.zeros((4000, 7))


ddir = input('data dir: ')
# ddir = "/mnt/storage/{}".format(
#     '{0:%Y-%m-%d-%H}h'.format(datetime.datetime.now()))
if os.path.isdir(ddir):
    pass
    # Previous following peice was to manual
    if 'y' != input('dir is already exists, continue? y/n'):
        import sys
        sys.exit()
else:
    os.mkdir(ddir)
t0 = time.time()
ct0 = time.ctime()
os.system("echo \"{}\" >> {}/0000.time".format(ct0, ddir))

# for el in range(-70,0, 10):
for el in range(-50, -10, 10):
    smc.goto(0, el, True)
    dBuf_img[:, :, :] = 0
    # dBuf_img1[:,:,:] = 0
    dBuf_ori[:, :] = 0
    count = 0
    time.sleep(.5)
    smc.goto(360, el, False)
    while 1:
        i, j, k, r = 0, 0, 0, 0  # bno.quaternion   # orientation
        ret, frame = cap.read()       # spectrum
        # ret1, frame1 = cap1.read()       # spectrum
        curazi = smc.get_pos_deg(1)  # orientation from motors
        print(count, ret, "%.2f" % curazi, i, el)
        if ret:       # and ret1:
            dBuf_img[count, :, :] = frame[:, 200:400, 0].reshape(200, 480)
            # dBuf_img1[count, :, :] = frame1[:, 200:400,  0].reshape(200, 480)
            dBuf_ori[count, :] = [el, curazi,  i, j, k, r,  time.time()-t0]
            count += 1
            # nm = '{:3.1f}_{:2.6f}_{:2.6f}_{:2.6f}_{:2.6f}'.format(el,i,j,k,r)
            # np.save('datasun/{}'.format(nm), frame[:,:,0])

        if abs(curazi - 360) < 0.2:
            break

    np.save('{}/img_el0_{:3.1f}'.format(ddir, el), dBuf_img[:count, :, :])
    # np.save('{}/img_el2_{:3.1f}'.format(ddir, el), dBuf_img1[:count, :,:])
    np.save('{}/ori_el__{:3.1f}'.format(ddir, el), dBuf_ori[:count, :])

    smc.goto(360, el+5, True)
    dBuf_img[:, :, :] = 0
    # dBuf_img1[:, :, :] = 0
    dBuf_ori[:, :] = 0
    count = 0
    time.sleep(.5)
    smc.goto(0, el+5, False)
    while 1:
        i, j, k, r = 0, 0, 0, 0      # bno.quaternion   # orientation
        ret, frame = cap.read()      # spectrum
        # ret1, frame1 = cap1.read() # spectrum
        curazi = smc.get_pos_deg(1)  # orientation from motors
        print(count, ret, "%.2f" % curazi, i)
        if ret:                      # and ret1:
            dBuf_img[count, :, :] = frame[:,  200:400, 0].reshape(200, 480)
            # dBuf_img1[count,:,:] = frame1[:, 200:400, 0].reshape(200,480)
            dBuf_ori[count, :] = [el+5, curazi, i, j, k, r,  time.time()-t0]
            count += 1
            # nm = '{:3.1f}_{:2.6f}_{:2.6f}_{:2.6f}_{:2.6f}'.format(el,i,j,k,r)
            # np.save('datasun/{}'.format(nm), frame[:,:,0])

        if abs(curazi - 0) < 0.2:
            break

    np.save('{}/img_el0_{:3.1f}'.format(ddir, el+5), dBuf_img[:count, :, :])
    # np.save('{}/img_el2_{:3.1f}'.format(ddir, el+5), dBuf_img1[:count, :,:])
    np.save('{}/ori_el__{:3.1f}'.format(ddir, el+5), dBuf_ori[:count, :])
