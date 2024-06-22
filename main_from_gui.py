import os
import time
import sys #datetime
import numpy as np
import cv2

#import board
#import busio
#import synscan
from custom_libs.sscan1 import Sscan
import queue
import threading


# ----------------------------------------------------------
class xVideoCapture:
    def __init__(self, name: str):
        self.cap = cv2.VideoCapture(name) # type: ignore
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
                    self.q.get_nowait()   # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
      return self.q.get()

# ----------------------------------------------------------
cli_args = {
    each_arg.split('=')[0]:each_arg.split('=')[1]
    for each_arg in sys.argv[1:]
    if each_arg.count('=') == 1
}

elv0 = int(cli_args["elv0"])
elv1 = int(cli_args["elv1"])
azi0 = int(cli_args["azi0"])
azi1 = int(cli_args["azi1"])

# ---------------------------------------------------------

#smc = synscan.motors()
smc = Sscan('/dev/ttyUSB0', 9600, 0.2)
smc.goto(0,0, True) # wait unitl the goto 0 0


cap0 = xVideoCapture("/dev/video0")
cap2 = xVideoCapture("/dev/video2")


#from adafruit_bno08x import (
#            BNO_REPORT_ACCELEROMETER,
#            BNO_REPORT_GYROSCOPE,
#            BNO_REPORT_MAGNETOMETER,
#            BNO_REPORT_ROTATION_VECTOR,
#            BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR,
#)
#from adafruit_bno08x.i2c import BNO08X_I2C

#i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
#bno = BNO08X_I2C(i2c)
#bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
#bno.enable_feature(BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR)





#cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
#cap1 = cv2.VideoCapture(2)
#cap1.set(cv2.CAP_PROP_BUFFERSIZE, 1)

dBuf_img0 = np.zeros((4000, 480, 640), dtype=np.uint8)
dBuf_img1 = np.zeros((4000, 480, 640), dtype=np.uint8)
dBuf_ori  = np.zeros((4000, 7))


ddir = cli_args["ddir"]
#ddir = "/mnt/storage/{}".format('{0:%Y-%m-%d-%H}h'.format(datetime.datetime.now()))
if os.path.isdir(ddir):
    pass
    #Previous following peice was to manual
else:
    os.mkdir(ddir)

t0 = time.time()
ct0 = time.ctime()
os.system("echo \"{}\" >> {}/0000.time".format(ct0, ddir))

#######################################################################################################################
for el in range(elv0, elv1, 10):
    smc.goto(azi0, el, True)
    dBuf_img0[:,:,:] = 0
    dBuf_img1[:,:,:] = 0
    dBuf_ori[:,:  ] = 0
    count=0
    time.sleep(.5)
    smc.goto(azi1, el, False)

    while 1:
        i,j,k,r = 0,0,0,0 #bno.quaternion      # orientation
        frame = cap0.read()               # spectrum
        curazi = smc.get_pos_deg(1)  # orientation from motors
        print(count, el, "%.2f" % curazi, time.time()-t0)
        dBuf_img0[count, :, :] = cap0.read()[:, :, 0] #frame[:, :, 0]
        dBuf_img1[count, :, :] = cap2.read()[:, :, 0] # frame[:, :, 0] #dBuf_img1[count,:,:] = frame1[:, 200:400, 0].reshape(200,480)
        dBuf_ori[count,:  ] = [el,curazi, i,j,k,r, time.time()-t0]
        count+=1

        if abs(curazi - azi1) < 0.2:
            break
    np.save('{}/img_el0_{:3.1f}'.format(ddir, el), dBuf_img0[:count, :,:])
    np.save('{}/img_el2_{:3.1f}'.format(ddir, el), dBuf_img1[:count, :,:])
    np.save('{}/ori_el__{:3.1f}'.format(ddir, el), dBuf_ori[:count, :  ])

    smc.goto(azi1, el+5,  True)
    dBuf_img0[:,:,:] = 0
    dBuf_img1[:,:,:] = 0
    dBuf_ori[:,:  ] = 0
    count=0
    time.sleep(.5)
    smc.goto(azi0, el+5, False)
    while 1:
        i,j,k,r = 0,0,0,0 #bno.quaternion      # orientation
        curazi = smc.get_pos_deg(1)  # orientation from motors
        print(count, el+5, "%.2f" % curazi, time.time()-t0)
        dBuf_img0[count,:,:] = cap0.read()[:, :, 0] #frame[:, 200:400, 0].reshape(200,480)
        dBuf_img1[count,:,:] = cap2.read()[:, :, 0] # frame1[:, 200:400, 0].reshape(200,480)
        dBuf_ori[count,:  ] = [el+5,curazi, i,j,k,r, time.time()-t0]
        count+=1

        if abs(curazi - azi0) < 0.2:
            break

    np.save('{}/img_el0_{:3.1f}'.format(ddir, el+5), dBuf_img0[:count, :,:])
    np.save('{}/img_el2_{:3.1f}'.format(ddir, el+5), dBuf_img1[:count, :,:])
    np.save('{}/ori_el__{:3.1f}'.format(ddir, el+5), dBuf_ori[:count, :  ])
