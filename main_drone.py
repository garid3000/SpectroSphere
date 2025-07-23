import os
import sys
import time
from datetime import datetime
import numpy as np
import cv2

import queue
import threading
import logging
import signal
from picamera2 import Picamera2  # pyright: ignore

# ================ setting the cli arugments =================================================
cli_args = {each_arg.split("=")[0]: each_arg.split("=")[1] for each_arg in sys.argv[1:] if each_arg.count("=") == 1}
cli_duration_in_s = int(cli_args["time"])
cli_batch_num_save = int(cli_args["batch"]) if "batch" in cli_args else 15000
cli_logging_lvl = logging.DEBUG if (("log" in cli_args) and (cli_args["log"] == "debug")) else logging.INFO
cli_path_spectr = cli_args["spectr"] if "spectr" in cli_args else "/dev/video0"
cli_path_webcam = cli_args["webcam"] if "webcam" in cli_args else None

cli_output_video = cli_args["out"] if "out" in cli_args else datetime.now().strftime("%Y%m%d-%H%M%S.avi")

outputting_stop_event = threading.Event()


# %%
def signal_handler(signum, frame):
    outputting_stop_event.set()


# %%
logging.basicConfig(
    filename=datetime.now().strftime("measurement-%Y%m%d-%H%M%S.log"),
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=cli_logging_lvl,
)


# %%
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})  # pyright: ignore
picam2.configure(video_config)  # pyright: ignore
picam2.start()  # pyright: ignore
time.sleep(1)  # Optional delay for exposure/white balance


# ================ camera handling thread class definition ===================================
class xVideoCapture:
    def __init__(self, name: str, fourcc: str = "MJPEG", autoexpo=3, fps=15, frame_w=640, frame_h=480):
        # ================ setting the camera setups =================================================
        self.cam_name = name
        self.cap = cv2.VideoCapture()  # type: ignore
        self.cap.open(name, apiPreference=cv2.CAP_V4L2)
        logging.info(f"cam_init: openning {name} camera")

        self.cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc("Y", "U", "Y", "V")
            if fourcc == "YUYV"
            else cv2.VideoWriter_fourcc("M", "J", "P", "G"),
        )
        logging.info(f"cam_init: setting {name} with {fourcc}")

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        logging.info(f"cam_init: setting {name} buffersize {1}")

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, autoexpo)
        logging.info(f"cam_init: setting {name} autoexposure {autoexpo}")

        self.cap.set(cv2.CAP_PROP_FPS, fps)
        logging.info(f"cam_init: setting {name} fps {fps}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_w)
        logging.info(f"cam_init: setting {name} w {frame_w}")

        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_h)
        logging.info(f"cam_init: setting {name} h {frame_h}")
        # ============================================================================================

        # =============== starting the queue =========================================================
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while not outputting_stop_event.is_set():
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
        print("xVideoCapture finished gracefully")

    def read(self):
        logging.debug(f"cam:{self.cam_name} frame sending")
        return self.q.get()


# %%
class xRpiCam:
    def __init__(self, frame_w: int = 640, frame_h: int = 480):
        # ================ setting the camera setups =================================================
        # Start the camera

        # =============== starting the queue =========================================================
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        # while True:
        while not outputting_stop_event.is_set():
            frame = picam2.capture_array()
            # logging.debug(f"cam:{self.cam_name} frame capture thread-wise")
            # if not ret:
            # break
            if not self.q.empty():
                try:
                    self.q.get_nowait()  # discard previous (unprocessed) frame
                except queue.Empty:
                    pass
            self.q.put(frame[:, :, :3])

        print("xRpiCam finished gracefully")

    def read(self):
        logging.debug(f"cam: frame sending")
        return self.q.get()


# %%
class Outputter:
    def __init__(
        self,
        output_video: str = "/tmp/out_ffv1.avi",
        str_4c: str = "FFV1",
        vid_h: int = 480,
        vid_w: int = 1280,
        fps: int = 10,
    ):
        # ================ setting the camera setups =================================================
        # Start the camera

        fourcc = cv2.VideoWriter_fourcc(*str_4c)

        ddir = os.path.join("/home/pi/", datetime.now().strftime("data_%Y%m%d_%H%M%S"))
        os.makedirs(ddir, exist_ok=True)
        logging.info(f"created the directory {ddir}")
        ct0 = time.ctime()
        os.system('echo "{}" >> {}/0000.time'.format(ct0, ddir))

        self.vid = cv2.VideoWriter(os.path.join(ddir, output_video), fourcc, fps, (vid_w, vid_h))

        # =============== starting the queue =========================================================
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._writer)
        self.t.daemon = True
        self.t.start()

    def _writer(self):
        while not outputting_stop_event.is_set():
            frame = self.q.get()
            self.vid.write(frame)
            # print(f"\t out-q size{self.q.qsize()}")

        self.vid.release()
        print("Outputter finished gracefully")


# %%


def main() -> int:
    cap0 = xVideoCapture(cli_path_spectr, fourcc="YUYV", fps=30, autoexpo=1)
    # cap2 = xVideoCapture("/dev/video2", fourcc="MJPG", autoexpo=3, frame_w=320, frame_h=240) ------ changed for usb3
    # cap2 = xVideoCapture("/dev/video2", fourcc="MJPG", autoexpo=3, frame_w=640, frame_h=480)
    cap2 = xRpiCam(frame_w=640, frame_h=480)
    out = Outputter(output_video=cli_output_video, str_4c="FFV1", vid_h=481, vid_w=1280, fps=7)

    logging.info("main-function: camera's initialized")

    t0 = time.perf_counter()
    vid_frame = np.empty((481, 1280, 3), np.uint8)
    count = 0
    forced_lag = 0
    while time.perf_counter() - t0 < cli_duration_in_s:
        # dBuf_img0[count, :, :] = cap0.read()[:, 200:400, 0]
        # dBuf_img1[count, :, :, :] = cap2.read()[:, :, :]
        # dBuf_ori[count, -1] = time.time() - t0

        vid_frame[:480, :640, :] = cap0.read()[:, :, :]
        vid_frame[:480, 640:, :] = cap2.read()[:, :, :]

        dt = time.perf_counter() - t0
        line_str = f"{dt}_{count}_{datetime.now().strftime('data_%Y%m%d_%H%M%S_')}"
        vid_frame[479, : len(line_str), 0] = np.frombuffer(line_str.encode(), count=len(line_str), dtype=np.uint8)[:]
        vid_frame[479, : len(line_str), 1] = np.frombuffer(line_str.encode(), count=len(line_str), dtype=np.uint8)[:]
        vid_frame[479, : len(line_str), 2] = np.frombuffer(line_str.encode(), count=len(line_str), dtype=np.uint8)[:]

        out.q.put(vid_frame.copy())
        print(
            count,
            f"{time.perf_counter() - t0:3.1f}s of {cli_duration_in_s}\t out_qsize:{out.q.qsize()=}\t {forced_lag=}",
        )
        count += 1

        if out.q.qsize() >= 30:
            time.sleep(0.2)
            forced_lag += 1

    outputting_stop_event.set()

    cap0.t.join()
    print("cap0 is done")
    cap2.t.join()
    print("cap2 is done")
    out.t.join()
    print("out is done")

    return 0


if __name__ == "__main__":
    sys.exit(main())
