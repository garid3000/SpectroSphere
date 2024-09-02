import os
import sys
import time
from datetime import datetime
import numpy as np
import cv2

import queue
import threading
import logging

# ================ setting the cli arugments =================================================
cli_args = {each_arg.split("=")[0]: each_arg.split("=")[1] for each_arg in sys.argv[1:] if each_arg.count("=") == 1}
cli_duration_in_s = int(cli_args["time"])
cli_batch_num_save = int(cli_args["batch"]) if "batch" in cli_args else 40000
cli_debug_or_info = logging.DEBUG if (("log" in cli_args) and (cli_args["log"] == "debug")) else logging.INFO

# ================ configuring the loggings ==================================================
logging.basicConfig(
    filename=datetime.now().strftime("measurement-%Y%m%d-%H%M%S.log"),
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=cli_debug_or_info,
)


# ================ camera handling thread class definition ===================================
class xVideoCapture:
    def __init__(self, name: str, fourcc: str = "MJPEG", autoexpo=3, fps=15, frame_w=640, frame_h=480):
        # ================ setting the camera setups =================================================
        self.cam_name = name
        self.cap = cv2.VideoCapture()  # type: ignore
        self.cap.open(name, apiPreference=cv2.CAP_V4L2)
        logging.info(f"cam_init: openning {name} camera")

        self.cap.set(cv2.CAP_PROP_FOURCC,
                     cv2.VideoWriter_fourcc("Y", "U", "Y", "V") if fourcc == "YUYV" else
                     cv2.VideoWriter_fourcc("M", "J", "P", "G"))
        logging.info(f"cam_init: setting {name} with {fourcc}")
                     
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE    , 1)
        logging.info(f"cam_init: setting {name} buffersize {1}")

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE , autoexpo)
        logging.info(f"cam_init: setting {name} autoexposure {autoexpo}")

        self.cap.set(cv2.CAP_PROP_FPS           , fps)
        logging.info(f"cam_init: setting {name} fps {fps}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH   , frame_w)
        logging.info(f"cam_init: setting {name} w {frame_w}")

        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT  , frame_h)
        logging.info(f"cam_init: setting {name} h {frame_h}")
        # ============================================================================================


        # =============== starting the queue =========================================================
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            logging.debug(f"cam:{self.cam_name} frame capture thread-wise")
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()  # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        logging.debug(f"cam:{self.cam_name} frame sending")
        return self.q.get()


# ---------------------------------------------------------

def main() -> int:
    cap0 = xVideoCapture("/dev/video0", fourcc="YUYV", fps=30, autoexpo=1)
    # cap2 = xVideoCapture("/dev/video2", fourcc="MJPG", autoexpo=3, frame_w=320, frame_h=240) ------ changed for usb3
    cap2 = xVideoCapture("/dev/video2", fourcc="MJPG", autoexpo=3, frame_w=640, frame_h=480)
    logging.info(f"main-function: camera's initialized")

    ddir = os.path.join(
        "/home/pi/",
        datetime.now().strftime("data_%Y%m%d_%H%M%S_") + cli_args["ddir"],
    )
    os.makedirs(ddir, exist_ok=True)
    logging.info(f"created the directory {ddir}")

    dBuf_img0 = np.memmap(os.path.join(ddir, "spectr.mmmp.npy"), mode="w+", shape=(cli_batch_num_save, 480, 200), dtype=np.uint8)
    dBuf_img1 = np.memmap(os.path.join(ddir, "webcam.mmmp.npy"), mode="w+", shape=(cli_batch_num_save, 640, 480), dtype=np.uint8)
    dBuf_ori  = np.memmap(os.path.join(ddir, "orient.mmmp.npy"), mode="w+", shape=(cli_batch_num_save, 7))
    logging.info(f"Creating the MemMap files")

    #dBuf_img0[:] = 0
    #dBuf_img1[:] = 0
    dBuf_ori[:] = 0

    t0 = time.time()
    ct0 = time.ctime()
    os.system('echo "{}" >> {}/0000.time'.format(ct0, ddir))

    #######################################################################################################################
    count = 0
    while (time.time() - t0 < cli_duration_in_s):
        dBuf_img0[count, :, :] = cap0.read()[:, 200:400, 0]
        dBuf_img1[count, :, :] = cap2.read()[:, :, 0]      
        dBuf_ori[count, -1] = time.time() - t0
        print(count, f"{time.time() - t0:3.2f}s", "of", cli_duration_in_s)
        count += 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
