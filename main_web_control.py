import os
import time
from datetime import datetime  # , date
from enum import Enum, auto
from io import BytesIO
import re

import base64
import cv2
import dash
import dash_bootstrap_components as dbc
import numpy as np
#import numpy.typing as npt
import plotly.graph_objs as go
#import qrcode
import queue
import subprocess
import threading

from PIL import Image
from dash import dcc, html, callback, Output, Input, State
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots


# %%
from custom_libs.sscan1 import Sscan

# %% plotly styles
tabs_styles = {
    #;"flexDirection": "row",  # Try to enforce horizontal layout
    "max-width": "none",
    "width": "90%"
    # "height": "44px"
}
tab_style = {}  # "borderBottom": "1px solid #d6d6d6", "padding": "6px"}  # , "fontWeight": "bold"


# %%
class DevState(Enum):
    waiting = auto()
    manual_camera = auto()
    manual_gimbal = auto()
    measurement_gimbal = auto()
    measurement_uav = auto()


class CmdType(Enum):
    do_nothing = auto()
    do_camera_preview = auto()
    do_camera_preview_with_set_expo = auto()
    do_motor_control = auto()
    ask_motor_status = auto()
    ask_thread_status = auto()
    start_motor_measurement = auto()
    start_uav_measurement = auto()


class RetType(Enum):
    motor_status = auto()
    preview_shot = auto()


class DashID(Enum):
    tab0 = auto()
    tab0_set_datep = auto()
    tab0_set_timeH = auto()
    tab0_set_timeM = auto()
    tab0_set_timeS = auto()

    tab1_expo_slidr = auto()
    tab1_gain_slidr = auto()
    tab1_1shot_bttn = auto()
    tab1_1shot_rslt = auto()
    tab1_rload_bttn = auto()
    tab1_figpreview = auto()
    tab1_oe_hist_gr = auto()

    tab2_live_motor = auto()
    tab2_cur_status = auto()
    tab2_elv_slider = auto()
    tab2_azi_slider = auto()
    tab2_bttn_motor = auto()
    tab2_bttn_reslt = auto()

    tab3_mtrms_cnf = auto()
    tab3_mtrms_res = auto()
    tab3_mtrms_liv = auto()
    tab3_mtr_elvrn = auto()
    tab3_mtr_azirn = auto()
    tab3_mtr_elvst = auto()
    tab3_mtr_azist = auto()
    tab3_mtrms_tag = auto()
    tab3_mtrms_btn = auto()
    tab3_mtr_elprg = auto()
    tab3_mtr_azprg = auto()

    tab4_rapid_cnf = auto()
    tab4_rapid_tag = auto()
    tab4_rapid_dur = auto()
    tab4_rapid_btn = auto()
    tab4_rapid_prg = auto()
    tab4_rapid_liv = auto()
    tab4_rapid_res = auto()


queue_cmd: "queue.Queue[tuple[CmdType, list[int|float]]]" = queue.Queue()
queue_reply: "queue.Queue[tuple[RetType, list[int|float]]]" = queue.Queue()
queue_shot_status: "queue.Queue[str]" = queue.Queue()
queue_rapid_progress: "queue.Queue[float]" = queue.Queue()
queue_motor_progress: "queue.Queue[tuple[ float,float ]]" = queue.Queue()
DATDIR = "/home/pi/data/"

# %%

marks_for_tab0_slider: dict[int, str] = {
    i: f"{i_expo:.2f}"
    for i, i_expo in zip(
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
        (0.03733, 0.14933, 0.52267, 1.08, 2.24, 4.48, 9.03, 18.14, 36.4, 72.99, 146.05, 292.21),
    )
}

tmp_tooltip = ({"always_visible": True, "style": {"color": "LightSteelBlue", "fontSize": "20px"}},)

# %%

class xVideoCapture:
    def __init__(self, name: str, fourcc: str = "MJPEG", autoexpo=3, fps=15, frame_w=640, frame_h=480):
        self.cap = cv2.VideoCapture()  # type: ignore
        self.cap.open(name, apiPreference=cv2.CAP_V4L2)
        if fourcc == "YUYV":
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "U", "Y", "V")) # pyright: ignore
        else:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G")) # pyright: ignore
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

    def set_exposure_gain(self, v4l2_int:int, v4l2_gain:int) -> None:
        self.cap.set(cv2.CAP_PROP_EXPOSURE, v4l2_int) # TODO need to check
        self.cap.set(cv2.CAP_PROP_GAIN, v4l2_gain)


# %%
class HardwareCtlThread(threading.Thread):
    def __init__(self, daemon: bool) -> None:
        super().__init__(daemon=daemon)
        print("hello from hrd ctl thread")

        self.cur_state: DevState = DevState.waiting
        self.cur_motor_evl: float = 0
        self.cur_motor_azi: float = 0

        # motor
        self.gimbal_motor: Sscan | None = None
        try:
            self.gimbal_motor = Sscan("/dev/ttyUSB0", 9600, 0.02)  # TODO "path may change", may need configure
        except Exception as e:
            print(f"Issue= {e}")
            self.gimbal_motor  = None

        # camera related

        self.cap0 = xVideoCapture("/dev/video0", fourcc="YUYV", fps=30, autoexpo=1)
        self.cap2 = xVideoCapture("/dev/video2", fourcc="MJPG", autoexpo=3, frame_w=320, frame_h=240)


    def run(self) -> None:
        #man_cam_param: list[int] = [1250, 1250, 1250, 1250]
        spect_expo  = 312 
        spect_gain  = 10

        ctrl_motor_elv = 0
        ctrl_motor_azi = 0

        meas_uav_tag: str = ""
        meas_uav_dur: float = 10

        tmp_elv_range: tuple[int, int] = (0, 1)
        tmp_azi_range: tuple[int, int] = (0, 1)
        tmp_data_tag  = ""

        while True:
            if self.cur_state == DevState.waiting:
                time.sleep(0.1)
                cmd, cmd_param = self.check_queue()

                if cmd == CmdType.do_camera_preview:
                    self.cur_state = DevState.manual_camera
                    assert len(cmd_param) == 2
                    spect_expo = int(cmd_param[0])
                    spect_gain = int(cmd_param[1])

                if cmd == CmdType.ask_motor_status:
                    self.do_send_motor_status()

                if cmd == CmdType.do_motor_control:
                    assert len(cmd_param) == 2
                    ctrl_motor_elv = cmd_param[0]
                    ctrl_motor_azi = cmd_param[1]
                    self.cur_state = DevState.manual_gimbal  # DONE maybe ok

                if cmd == CmdType.start_uav_measurement:
                    assert len(cmd_param) == 2
                    assert isinstance(cmd_param[0], str)
                    meas_uav_tag = cmd_param[0]
                    meas_uav_dur = cmd_param[1] * 60
                    print(cmd_param[1], meas_uav_dur)
                    print(f"{ meas_uav_dur=}")
                    self.cur_state = DevState.measurement_uav
                if cmd == CmdType.start_motor_measurement:   
                    #assert len(cmd_param) == 7  #
                    # TODO check the above
                    self.cur_state = DevState.measurement_gimbal

                    tmp_elv_range = (int(cmd_param[0]), int(cmd_param[1]))
                    tmp_azi_range = (int(cmd_param[2]), int(cmd_param[3]))
                    tmp_data_tag  = cmd_param[4]


            elif self.cur_state == DevState.manual_camera:
                self.do_manual_camera(spect_expo, spect_gain)
                self.cur_state = DevState.waiting
            elif self.cur_state == DevState.manual_gimbal:
                self.do_manual_gimbal(ctrl_motor_elv, ctrl_motor_azi)
                self.cur_state = DevState.waiting
            elif self.cur_state == DevState.measurement_gimbal:
                self.do_measurement_gimbal(
                    tmp_elv_range ,tmp_azi_range, tmp_data_tag,
                )
                self.cur_state = DevState.waiting
            elif self.cur_state == DevState.measurement_uav:
                print(f"{ meas_uav_dur=}")
                self.do_measurement_uav( # TODO
                    meas_uav_tag,
                    meas_uav_dur,
                    expo = spect_expo,
                    gain = spect_gain,
                )
                self.cur_state = DevState.waiting
            else:
                pass  # PANIC, shouldn't be here

    def check_queue(self) -> tuple[CmdType, list[int | float]]:
        try:
            cmd_type, cmd_param = queue_cmd.get_nowait()  #
            queue_cmd.task_done()
            return cmd_type, cmd_param
        except queue.Empty:
            time.sleep(0.1)
            return CmdType.do_nothing, []
        except Exception as e:
            print("except Exception as e:", e)
            return CmdType.do_nothing, []

    def do_send_motor_status(self) -> None:
        val1 = 6789
        val2 = -12345

        if self.gimbal_motor:
            val1 = self.gimbal_motor.get_pos_deg(1)
            val2 = self.gimbal_motor.get_pos_deg(2)
        queue_reply.put((RetType.motor_status, [val1, val2]))
        self.cur_state = DevState.waiting

    def do_manual_camera(self, v4l2_expo: int, v4l2_gain: int) -> None:
        self.cap0.set_exposure_gain(v4l2_expo, v4l2_gain) # TODO
        
        tmp0 = self.cap0.read()
        tmp2 = self.cap2.read()

        queue_shot_status.put("Done measurement")
        np.save("/tmp/tmp0.npy", tmp0)
        np.save("/tmp/tmp2.npy", tmp2)

    def do_manual_gimbal(self, elv: int | float, azi: int | float) -> None:
        if self.gimbal_motor:
            self.gimbal_motor.goto(azi, elv)

    def do_measurement_gimbal(self, elv_range:tuple[int, int], azi_range:tuple[int, int], data_tag:str) -> None: # TODO
        self.dBuf_img0 = np.zeros((4000, 480, 200), dtype=np.uint8)
        self.dBuf_img1 = np.zeros((4000, 240, 320), dtype=np.uint8)
        self.dBuf_ori  = np.zeros((4000, 7))

        elv0, elv1 = int(elv_range[0]), int(elv_range[1]+1)
        azi0, azi1 = int(azi_range[0]), int(azi_range[1]+1)
        t0 = time.time()

        tmp_data_tag = re.sub(r'\W+', "", data_tag)
        start_ymd_hms = datetime.now().strftime("%Y%m%d_%H%M%S")
        ddir = f"{DATDIR}/GIMBAL_{start_ymd_hms}_{tmp_data_tag}"
        os.makedirs(ddir, exist_ok=True)

        if self.gimbal_motor is None:
            print("no motor")
            return

        for el in range(elv0, elv1, 10):
            self.gimbal_motor.goto(azi0, el, True)
            self.dBuf_img0[:, :, :] = 0
            self.dBuf_img1[:, :, :] = 0
            self.dBuf_ori[:, :] = 0
            count = 0
            time.sleep(0.5)
            self.gimbal_motor.goto(azi1, el, False)

            while 1:
                i, j, k, r = 0, 0, 0, 0 #i, j, k, r = snsr.read()  # bno.quaternion      # orientation
                curazi = self.gimbal_motor.get_pos_deg(1)  # orientation from motors
                print(count, el, "%.2f" % curazi, time.time() - t0, i, j, k, r)
                self.dBuf_img0[count, :, :] = self.cap0.read()[:, 200:400, 0]
                self.dBuf_img1[count, :, :] = self.cap2.read()[:, :, 0]
                self.dBuf_ori[count, :] = [el, curazi, i, j, k, r, time.time() - t0]
                count += 1

                if abs(curazi - azi1) < 0.2:
                    break

                if (count % 20) == 0:
                    queue_motor_progress.put((( el - elv0 ) / (elv1-elv0), ( curazi - azi0 ) / (azi1 - azi0)))

            print('cpmressing to save', "{}/scan_data_{:3.1f}".format(ddir, el)) 
            np.savez_compressed( # TODO later lossless video needed
                "{}/scan_data_{:3.1f}".format(ddir, el),
                spectr=self.dBuf_img0[:count, :, :],
                webcam=self.dBuf_img1[:count, :, :],
                orient=self.dBuf_ori[:count, :],
            )


            self.gimbal_motor.goto(azi1, el + 5, True)
            self.dBuf_img0[:, :, :] = 0
            self.dBuf_img1[:, :, :] = 0
            self.dBuf_ori[:, :] = 0
            count = 0
            time.sleep(0.5)
            self.gimbal_motor.goto(azi0, el + 5, False)
            while 1:
                i, j, k, r = 0, 0, 0, 0
                curazi = self.gimbal_motor.get_pos_deg(1)  # orientation from motors
                print(count, el + 5, "%.2f" % curazi, time.time() - t0)
                self.dBuf_img0[count, :, :] = self.cap0.read()[:, 200:400, 0]  # frame[:, 200:400, 0].reshape(200,480)
                self.dBuf_img1[count, :, :] = self.cap2.read()[:, :, 0]  # frame1[:, 200:400, 0].reshape(200,480)
                self.dBuf_ori[count, :] = [el + 5, curazi, i, j, k, r, time.time() - t0]
                count += 1

                if abs(curazi - azi0) < 0.2:
                    break

                if (count % 20) == 0:
                    queue_motor_progress.put((( ( el + 5 ) - elv0 ) / (elv1-elv0), ( curazi - azi0 ) / (azi1 - azi0)))

            np.savez_compressed(
                "{}/scan_datA_{:3.1f}".format(ddir, el + 5),
                spectr=self.dBuf_img0[:count, :, :],
                webcam=self.dBuf_img1[:count, :, :],
                orient=self.dBuf_ori[:count, :],
            )
            print('cpmressing to save', "{}/scan_datA_{:3.1f}".format(ddir, el + 5))

        queue_motor_progress.put((1, 1))

    def do_measurement_uav(
            self,
            data_tag: str,
            duration_sec: int | float = 100,
            expo: int = 312,
            gain: int = 20,
    ) -> None:
        self.cap0.set_exposure_gain(expo, gain) # TODO
        pass
        #print(f"starting UAV measure for {duration_sec} sec")
        #with lock_fbframe:
        #    fbframe[:, :, :] = 0

        #init_time = time.perf_counter()
        #start_ymd_hms = datetime.now().strftime("%Y%m%d_%H%M%S")
        #tmp_data_tag = re.sub(r'\W+', '', data_tag)
        #tmp_data_dir = f"{DATDIR}/UAV_{start_ymd_hms}_{tmp_data_tag}"
        #os.makedirs(tmp_data_dir, exist_ok=True)
        #shotcount = 0
        #while True:
        #    shotcount += 1
        #    cur_time = time.perf_counter()
        #    if cur_time - init_time > duration_sec:
        #        queue_rapid_progress.put(1)
        #        break
        #    queue_rapid_progress.put((cur_time - init_time) / duration_sec)
        #    print("\t, inside doing, measurement:", (cur_time - init_time) / duration_sec)

        #    #img0123 = self.capture_img([2500, 2500, 2500, 2500])
        #    img0123 = self.capture_img([e1, e2, e3, e4])
        #    ymd_hms_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        #    save_fname = f"{ymd_hms_tag}_{shotcount:05d}_{e1:04d}_{e2:04d}_{e3:04d}_{e4:04d}"

        #    cv2.imwrite(f"{tmp_data_dir}/{save_fname}.tif", img0123)

    # def capture_img(self, expos: list[int]) -> npt.NDArray[np.uint8]:
    #     # , q_send_status_to: "queue.Queue[str] | None" = None
    #     assert len(expos) == 4, f"bad expo.s lenght {expos}"
    #     # fs = [None, None, None, None]
    #     res_img = np.zeros((480, 640 * 4, 3), dtype=np.uint8)
    #     print(f"capturing 8img at {expos}")
    #     for i in range(4):
    #         self.caps[i].open(self.vid_dev_path[i], apiPreference=cv2.CAP_V4L2)
    #         self.caps[i].set(cv2.CAP_PROP_EXPOSURE, expos[i])
    #         time.sleep(0.010)
    #         self.caps[i].grab()
    #         self.caps[i].grab()
    #         ret_i, frame_i = self.caps[i].retrieve()
    #         if ret_i:
    #             res_img[:, i * 640 : (i + 1) * 640, :] = frame_i[:, :, :]
    #             print("+", self.vid_dev_path[i])
    #         else:
    #             print("-", self.vid_dev_path[i])
    #         self.caps[i].release()
    #         # if q_send_status_to:
    #         # q_send_status_to.put(f"shotting-{i}")
    #         time.sleep(0.05)

    #     # if q_send_status_to:
    #     #    q_send_status_to.put(f"Done")
    #     return res_img

    # def camera_inits(self) -> None:
    #     for i in range(4):
    #         self.caps[i].open(self.vid_dev_path[i], apiPreference=cv2.CAP_V4L2)
    #         self.caps[i].set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("Y", "U", "Y", "V"))  # pyright: ignore
    #         self.caps[i].set(cv2.CAP_PROP_BUFFERSIZE, 1)
    #         self.caps[i].set(cv2.CAP_PROP_APERTURE, 1)
    #         self.caps[i].set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 is manual
    #         self.caps[i].set(cv2.CAP_PROP_GAIN, 1)  # 1 is manual
    #         print(
    #             "init",
    #             i,
    #             self.caps[i].get(cv2.CAP_PROP_FOURCC),
    #             self.caps[i].get(cv2.CAP_PROP_BUFFERSIZE),
    #         )
    #         self.caps[i].release()

    # def test_exposure(self, expos1: list[int], expos2: list[int], expos3: list[int]) -> None:
    #     # fname = "/tmp/test.png"
    #     img = cv2.vconcat(
    #         [
    #             self.capture_img(expos1),
    #             self.capture_img(expos2),
    #             self.capture_img(expos3),
    #         ]
    #     )
    #     # img = capture_img(expos1)
    #     img[img >= 253] = 0
    #     # cv2.imwrite(fname, img)
    #     self.img = img


# %%


class DashAppThread(threading.Thread):
    def __init__(self, daemon: bool, host="0.0.0.0", port=42263, debug=False):
        super().__init__(daemon=daemon)
        self.host = host
        self.port = port
        self.debug = debug

        #self.wifi_ip = get_ip_dict()["wlan0"]
        #self.qr = qrcode.QRCode(
        #    version=1,
        #    error_correction=qrcode.constants.ERROR_CORRECT_L,  # pyright: ignore
        #    box_size=10,
        #    border=4,
        #)
        #self.qr.add_data(f"http://{self.wifi_ip}:{port}")
        #self.qr.make(fit=True)

    def run(self):
        # self.display_qr_code()
        # app = dash.Dash(__name__)
        app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        app.css.config.serve_locally = True  # for the offline usage
        app.scripts.config.serve_locally = True # for the offline usage

        app.layout = html.Div(
            children=[
                html.H1(children="4BC: Web-control"),
                # html.Div(children="Dash: A web application framework for Python."),
                dbc.Tabs(#dcc.Tabs(
                    #id="tabs-with-classes",
                    #value="tabs-1",
                    #parent_className="custom-tabs",
                    #className="custom-tabs-container",
                    children=[
                        dbc.Tab(
                            label="System",
                            #value="tab-0", #className="custom-tab",
                            #selected_className="custom-tab--selected",
                            #style={"display": "flex", "alignItems": "center"},
                            children=[
                                dcc.Interval(id="interval-component", interval=1000, n_intervals=0),
                                html.Div(
                                    style={"display": "flex"},
                                    children=[
                                        # tab0
                                        html.Div(
                                            children="Current time",
                                            id="tab0-time",
                                            style={
                                                "border": "1px solid #ccc",
                                                "borderRadius": "5px",
                                                "padding": "10px",
                                                "margin": "10px 0",
                                            },
                                        ),
                                        html.Div(
                                            style={
                                                "border": "1px solid #ccc",
                                                "borderRadius": "5px",
                                                "padding": "10px",
                                                "margin": "10px 0",
                                            },
                                            children=[


                                dbc.Row(
                                    [
                                        dbc.Label("New date", html_for=DashID.tab0_set_datep.name, width=3),
                                        dbc.Col(
                                            dcc.DatePickerSingle(id=DashID.tab0_set_datep.name, date=datetime.now().strftime("%Y-%m-%d")),
                                            width=9,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("New time", html_for=DashID.tab0_set_timeH.name, width=3),
                                        dbc.Col(
                                            dcc.Input(value=datetime.now().hour, id=DashID.tab0_set_timeH.name, type="number", min=0, max=23, step=1),
                                            width=3,
                                        ),
                                        dbc.Col(
                                            dcc.Input(value=datetime.now().minute, id=DashID.tab0_set_timeM.name, type="number", min=0, max=59, step=1),
                                            width=3,
                                        ),
                                        dbc.Col(
                                            dcc.Input(value=datetime.now().minute, id=DashID.tab0_set_timeS.name, type="number", min=0, max=59, step=1),
                                            width=3,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("Auto sync (via Internet)", html_for=DashID.tab0_set_timeH.name, width=3),
                                        dbc.Col(
                                                                dcc.Checklist(
                                                                    id="tab0-time-ntp-sync",
                                                                    options=[{"label": "enable", "value": "checked"}],
                                                                    value=[],
                                                                ),
                                            width=3,
                                        ),
                                    ],
                                    className="mb-3",
                                ),


                                                                html.Div(
                                                                    children=" ",
                                                                    id="tab0-time-change-button-last-time-change",
                                                                ),

                                                                html.Button("Change", id="tab0-time-change-button"),

                                                dcc.ConfirmDialog(
                                                    id="tab0-time-change-confirmaton",
                                                    message="Are you sure you want to proceed?",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        dbc.Tab(
                            label="Camera",
                            children=[
                                dbc.Row(
                                    [
                                        dbc.Label("Spectrometer expo", html_for=DashID.tab1_expo_slidr.name, width=3),
                                        dbc.Col(
                                            dcc.Slider(0, 11, 1, value=5, id=DashID.tab1_expo_slidr.name, marks=marks_for_tab0_slider), width=9,), # pyright: ignore
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("Spectrometer gain", html_for=DashID.tab1_gain_slidr.name, width=3, ),
                                        dbc.Col(dcc.Slider(0, 33, value=8, id=DashID.tab1_gain_slidr.name, tooltip={"placement": "top", "always_visible": True}), width=9, ), # pyright: ignore
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("Start measurement", html_for=DashID.tab1_1shot_bttn.name, width=3),
                                        dbc.Col(
                                            dbc.Button("Shot", id=DashID.tab1_1shot_bttn.name, color="primary", size="lg"),
                                            width=3,
                                        ),
                                        dbc.Col(
                                            dcc.Loading([html.Div(children="", id=DashID.tab1_1shot_rslt.name)]),
                                            width=4,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("Download & Show", html_for=DashID.tab1_rload_bttn.name, width=3),
                                        dbc.Col(
                                            dbc.Button("Reload", id=DashID.tab1_rload_bttn.name, color="primary", size="lg"),
                                            width=3,
                                        ),
                                    ],
                                    className="mb-3",
                                ),


                                dcc.Loading(
                                    children=[
                                        dcc.Graph(id=DashID.tab1_oe_hist_gr.name),
                                        html.Img(id=DashID.tab1_figpreview.name, style={"width": "80%"}),
                                    ],
                                ),
                                # dcc.Interval(id=DashID.tab1_live_inter.name, interval=5000, n_intervals=0),
                                # html.Div(children="", id=DashID.tab1_live_outpt.name),
                            ],
                        ),
                        dbc.Tab(#dcc.Tab(
                            label="Motor",
                            children=[
                                dcc.Interval(id=DashID.tab2_live_motor.name, interval=1000, n_intervals=0),
                                #html.Div(id=DashID.tab2_cur_status.name),

                                dbc.Row(
                                    [
                                        dbc.Label("Current Motor:", html_for=DashID.tab2_cur_status.name, width=3),
                                        dbc.Col(html.Div(id=DashID.tab2_cur_status.name), width=9,),
                                    ],
                                    className="mb-3",
                                ),


                                dbc.Row(
                                    [
                                        dbc.Label("ELV-ctrl: ", html_for=DashID.tab2_elv_slider.name, width=3),
                                        dbc.Col(
                                            dcc.Slider(-90, 90, value=0, id=DashID.tab2_elv_slider.name, tooltip={"placement": "top", "always_visible": True}),
                                            width=9,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("AZI-ctrl: ", html_for=DashID.tab2_azi_slider.name, width=3),
                                        dbc.Col(
                                            dcc.Slider(-180, 180, value=0, id=DashID.tab2_azi_slider.name, tooltip={"placement": "top", "always_visible": True}),
                                            width=9,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("Command Send", html_for=DashID.tab2_bttn_motor.name, width=3),
                                        dbc.Col(
                                            #html.Button("Send Command", id=DashID.tab2_bttn_motor.name, n_clicks=0,),
                                            dbc.Button("Send", id=DashID.tab2_bttn_motor.name, color="primary", size="lg"),
                                            width=4,
                                        ),
                                        dbc.Col(
                                            html.Th(children="", id=DashID.tab2_bttn_reslt.name),
                                            width=4,
                                        ),
                                    ],
                                    className="mb-3",
                                ),

                            ],
                        ),
                        dbc.Tab(#dcc.Tab(
                            label="Measurement (motorized)",
                            children=[
                                dcc.ConfirmDialog(id=DashID.tab3_mtrms_cnf.name, message="Are you sure you want to measurement?"),
                                dcc.Interval(id=DashID.tab3_mtrms_liv.name, interval=1000, n_intervals=0),
                                html.Div(id=DashID.tab3_mtrms_res.name),
                                dbc.Row(
                                    [
                                        dbc.Label("ELV Range: ", html_for=DashID.tab3_mtr_elvrn.name, width=3),
                                        dbc.Col(
                                            dcc.RangeSlider(
                                                -90,
                                                90,
                                                #5,
                                                value=[-30, 0],
                                                id=DashID.tab3_mtr_elvrn.name,
                                                tooltip={"placement": "top", "always_visible": True},
                                                allowCross=False
                                            ),
                                            width=9,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("AZI Range: ", html_for=DashID.tab3_mtr_azirn.name, width=3),
                                        dbc.Col(
                                            dcc.RangeSlider(
                                                -180,
                                                180,
                                                #5,
                                                value=[-90, 90],
                                                id=DashID.tab3_mtr_azirn.name,
                                                tooltip={"placement": "bottom", "always_visible": True},
                                                allowCross=False
                                            ),
                                            width=9,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                #dbc.Row(
                                #    [
                                #        dbc.Label("ELV step: ", html_for=DashID.tab3_mtr_elvst.name, width=3),
                                #        dbc.Col(
                                #            dbc.Input(
                                #                value = 10, type="number", id=DashID.tab3_mtr_elvst.name, placeholder="Enter step",
                                #            ),
                                #            width=9,
                                #        ),
                                #    ],
                                #    className="mb-3",
                                #),
                                #dbc.Row(
                                #    [
                                #        dbc.Label("AZI step: ", html_for=DashID.tab3_mtr_azist.name, width=3),
                                #        dbc.Col(
                                #            dbc.Input(
                                #                value = 10, type="number", id=DashID.tab3_mtr_azist.name, placeholder="Enter step",
                                #            ),
                                #            width=9,
                                #        ),
                                #    ],
                                #    className="mb-3",
                                #),

                                dbc.Row(
                                    [
                                        dbc.Label("Data Tag", html_for=DashID.tab3_mtrms_tag.name, width=3),
                                        dbc.Col(
                                            dbc.Input(
                                                type="text", id=DashID.tab3_mtrms_tag.name, placeholder="Enter text explaining about this measurement.",
                                            ),
                                            width=9,
                                        ),

                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("Start measurement", html_for=DashID.tab3_mtrms_btn.name, width=3),
                                        dbc.Col(
                                            dbc.Button(
                                                "Start",
                                                id=DashID.tab3_mtrms_btn.name,
                                                color="primary",
                                                size="lg",
                                            ),
                                            width=9,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("Measurement ELV", html_for=DashID.tab3_mtr_elprg.name, width=3),
                                        dbc.Col(dbc.Progress(id=DashID.tab3_mtr_elprg.name), width=9),
                                    ],
                                    className="mb-3",
                                ),

                                dbc.Row(
                                    [
                                        dbc.Label("Measurement AZI", html_for=DashID.tab3_mtr_azprg.name, width=3),
                                        dbc.Col(dbc.Progress(id=DashID.tab3_mtr_azprg.name), width=9),
                                    ],
                                    className="mb-3",
                                ),

                            ],
                        ),
                        dbc.Tab(#dcc.Tab(
                            label="Measurement (UAV)",
                            # value="tab-4",
                            # className="custom-tab",
                            # selected_className="custom-tab--selected",
                            # style=tab_style,
                            children=[
                                dcc.ConfirmDialog(
                                    id=DashID.tab4_rapid_cnf.name, message="Are you sure you want to measurement?"
                                ),
                                dcc.Interval(id=DashID.tab4_rapid_liv.name, interval=1000, n_intervals=0),
                                dbc.Row(
                                    [
                                        dbc.Label("Data tag", html_for=DashID.tab4_rapid_tag.name, width=3),
                                        dbc.Col(
                                            dbc.Input(
                                                type="text", id=DashID.tab4_rapid_tag.name, placeholder="Enter Tag"
                                            ),
                                            width=5,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("Data duration (min)", html_for=DashID.tab4_rapid_dur.name, width=3),
                                        dbc.Col(
                                            dbc.Input(
                                                type="number",
                                                value=20,
                                                id=DashID.tab4_rapid_dur.name,
                                                placeholder="Enter duration (min)",
                                            ),
                                            width=5,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("Start measurement", html_for=DashID.tab4_rapid_btn.name, width=3),
                                        dbc.Col(
                                            dbc.Button(
                                                "Start",
                                                id=DashID.tab4_rapid_btn.name,
                                                color="primary",
                                                size="lg",
                                            ),
                                            width=5,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Label("Measurement status", html_for=DashID.tab4_rapid_prg.name, width=3),
                                        dbc.Col(dbc.Progress(id=DashID.tab4_rapid_prg.name), width=5),
                                    ],
                                    className="mb-3",
                                ),
                                html.Div("", id=DashID.tab4_rapid_res.name),
                            ],
                        ),
                    ],
                    style=tabs_styles,
                ),
            ]
        )
        app.run(host=self.host, port=self.port, debug=self.debug)

    # def display_qr_code(self):
    #     with lock_fbframe:
    #         fbframe[:, :, :] = 0
    #         qrmatrix: npt.NDArray[np.bool] = np.array(self.qr.get_matrix())
    #         qr_size = qrmatrix.shape[0]
    #         px_per_cell = (320 - 100) // qr_size
    #         print(px_per_cell)
    #         for i in range(qr_size):
    #             for j in range(qr_size):
    #                 fbframe[
    #                     50 + px_per_cell * i : 50 + px_per_cell * (i + 1),
    #                     140 + px_per_cell * j : 140 + px_per_cell * (j + 1),
    #                     :,
    #                 ] = 255 if qrmatrix[i, j] else 0

    #         cv2.putText(fbframe, f"http://{self.wifi_ip}:{self.port}", (30, 270), CVFONT, 1, CLRWHT, 4, LINEAA)

    @callback(
        Output(component_id="tab0-time", component_property="children"),
        Input(component_id="interval-component", component_property="n_intervals"),
    )
    def update_tab0(n):
        # print(f"internval #1, {n}")
        now = datetime.now()

        return html.Div(
            [
                html.Table(
                    [
                        html.Tr([html.Th("Current time")]),
                        html.Tr([html.Th("System-Date:"), html.Div(now.strftime("%Y/%m/%d (%a)"))]),
                        html.Tr([html.Th("System-Time:"), html.Div(now.strftime("%H:%M:%S"))]),
                    ]
                ),
            ]
        )

    @callback(
        Output("tab0-time-change-confirmaton", "displayed"),
        Input("tab0-time-change-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def callback_confirm_about_time_set(_):
        return True

    @callback(
        Output("tab0-time-change-button-last-time-change", "children"),
        Input("tab0-time-change-confirmaton", "submit_n_clicks"),
        State(DashID.tab0_set_timeH.name, "value"),
        State(DashID.tab0_set_timeM.name, "value"),
        State(DashID.tab0_set_timeS.name, "value"),
        State(DashID.tab0_set_datep.name, "date"),
        State("tab0-time-ntp-sync", "value"),
        prevent_initial_call=True,
    )
    def callback_actual_time_change(confirm_n_clicks, h: int, m: int, s: int, Y_m_d: str, checked_state: list[str]):
        # print(confirm_n_clicks, h, m, s, Y_m_d)
        res = ""

        if not confirm_n_clicks:
            return ""

        subprocess.call(["sudo", "timedatectl", "set-ntp", "false"])
        subprocess.call(["sudo", "timedatectl", "set-time", f"{Y_m_d} {h}:{m}:{s}"])

        res += f"{Y_m_d} {h}:{m}:{s}"
        if "checked" in checked_state:
            subprocess.call(["sudo", "timedatectl", "set-ntp", "true"])
            res += "\t +auto-internet-sync"

        return res

    @callback(
        Output(component_id=DashID.tab2_cur_status.name, component_property="children"),
        Input(component_id=DashID.tab2_live_motor.name, component_property="n_intervals"),
    )
    def update_tab2_interval_for_motor(n):
        queue_cmd.put((CmdType.ask_motor_status, []))

        try:
            cmd_type, cmd_param = queue_reply.get(timeout=2)  #
            queue_reply.task_done()
            if cmd_type == RetType.motor_status:
                return html.Div(
                    [
                        html.Table(
                            [
                                html.Tr([html.Th(children="Current: ELV "), html.Div(children=f"{cmd_param[1]:0.1f}")]),
                                html.Tr([html.Th(children="Current: AZI "), html.Div(children=f"{cmd_param[0]:0.1f}")]),
                            ]
                        ),
                    ]
                )
        except queue.Empty:
            time.sleep(0.1)
            raise PreventUpdate
        except Exception as e:
            print("except Exception as e:", e)
            raise PreventUpdate

    @callback(
        Output(DashID.tab2_bttn_reslt.name, "children"),
        Input(DashID.tab2_bttn_motor.name, "n_clicks"),
        State(DashID.tab2_elv_slider.name, "value"),
        State(DashID.tab2_azi_slider.name, "value"),
        prevent_initial_call=True,
    )
    def callback_tab2_motor_send(n, elv, azi):
        res = ""
        print(n, type(n), elv, type(elv), azi, type(azi))
        queue_cmd.put((CmdType.do_motor_control, [elv, azi]))
        return res

    @callback(
        Output(DashID.tab1_1shot_rslt.name, "children"),
        Input(DashID.tab1_1shot_bttn.name, "n_clicks"),
        State(DashID.tab1_expo_slidr.name, "value"),
        State(DashID.tab1_gain_slidr.name, "value"),
        prevent_initial_call=True,
        running=[(Output(DashID.tab1_1shot_bttn.name, "disabled"), True, False)],
    )
    def callback_tab1_cam_shot(n, spec_expo, spec_gain):
        res = f"{ n=}, {spec_expo=} {spec_gain=}"
        print(res)

        expo_v4l2_vals = (1, 2, 5, 10, 20, 39, 78, 156, 312, 625, 1250, 2500)
        queue_cmd.put(
            (CmdType.do_camera_preview, [expo_v4l2_vals[spec_expo], spec_gain])
        )

        try:
            status = queue_shot_status.get(timeout=10)
            if not isinstance(status, str):
                raise PreventUpdate
            return status + f"{queue_shot_status.qsize()=}" + res

        except Exception as e:
            # raise PreventUpdate
            return str(e)

    @callback(
        Output(component_id=DashID.tab1_figpreview.name, component_property="src"),
        Output(component_id=DashID.tab1_oe_hist_gr.name, component_property="figure"),
        Input(DashID.tab1_rload_bttn.name, "n_clicks"),
        prevent_initial_call=True,
        running=[(Output(DashID.tab1_rload_bttn.name, "disabled"), True, False)],
    )
    def callback_tab1_reload_show(n):
        def array_to_base64(array):
            oe = np.where(array[:, :, 0] > 250)
            array[oe[0], oe[1], 2] = 0
            array[oe[0], oe[1], 1] = 0
            array[oe[0], oe[1], 0] = 255
            im = Image.fromarray(array[::2, ::2, :])  # Convert to 8-bit image
            buffered = BytesIO()
            im.save(buffered, format="PNG")
            # im.save(buffered, format="JPG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return "data:image/png;base64," + img_str

        tmp_spec_img = np.load("/tmp/tmp0.npy")
        tmp_wbcm_img = np.load("/tmp/tmp2.npy")

        fig = make_subplots(rows=1, cols=2)

        fig.add_trace(
            go.Heatmap(z=tmp_spec_img[:, :, 0], zmin=0, zmax=255, showscale=True, colorscale="Viridis"),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Heatmap(z=tmp_wbcm_img[:, :, 0], zmin=0, zmax=255, showscale=True, colorscale="Gray",),
            row=1,
            col=2,
        )
        fig.update_yaxes(autorange="reversed", row=1, col=1)
        fig.update_yaxes(autorange="reversed", row=1, col=2)

        fig.update_layout(
            title="Camera Preview",
            #xaxis_title="Value",
            #yaxis_title="Number of Pixels",
            #barmode="overlay",
        )

        return array_to_base64(tmp_spec_img), fig

    @callback(
        Output(DashID.tab3_mtrms_cnf.name, "displayed"),
        Input(DashID.tab3_mtrms_btn.name, "n_clicks"),
        prevent_initial_call=True,
    )
    def callback_tab3_confirmation(_):
        #Dprint("what")
        return True

    @callback(
        Output(DashID.tab3_mtrms_res.name, "children"),
        Input(DashID.tab3_mtrms_cnf.name, "submit_n_clicks"),
        State(DashID.tab3_mtr_elvrn.name, "value"),
        State(DashID.tab3_mtr_azirn.name, "value"),
        State(DashID.tab3_mtrms_tag.name, "value"),
        prevent_initial_call=True,
    )
    def callback_tab3_start_measurement(confirm_n_clicks, elv_range, azi_range, data_tag):
        print("asdf asdf", elv_range, type(elv_range))

        tmp_data_tag = data_tag if isinstance(data_tag, str) else "tmp_data"
        queue_cmd.put(
            (CmdType.start_motor_measurement, [elv_range[0], elv_range[1], azi_range[0], azi_range[1], tmp_data_tag])
        )
        return ""

    @callback(
        Output(component_id=DashID.tab3_mtr_elprg.name, component_property="value"),
        Output(component_id=DashID.tab3_mtr_elprg.name, component_property="label"),
        Output(component_id=DashID.tab3_mtr_azprg.name, component_property="value"),
        Output(component_id=DashID.tab3_mtr_azprg.name, component_property="label"),

        #Output(component_id=DashID.tab4_rapid_prg.name, component_property="label"),
        Input(component_id=DashID.tab3_mtrms_liv.name, component_property="n_intervals"),
    )
    def callback_tab3_live_interval(n):  # -> tuple[float, str]:
        #res = 0
        print("callback_tab3_live_interval(n)")
        try:
            x, y = queue_motor_progress.get_nowait()
            x, y = x*100, y*100
            print(x, y)
            #print(f"{res:.2f}%")
            return (
                x,
                f"{x:.0f} %" if x >= 5 else "",
                y,
                f"{y:.0f} %" if y >= 5 else "",
            )
        except Exception as e:
            print(e)
            raise PreventUpdate


    @callback(
        Output(DashID.tab4_rapid_cnf.name, "displayed"),
        Input(DashID.tab4_rapid_btn.name, "n_clicks"),
        prevent_initial_call=True,
    )
    def callback_tab4_confirmation(_):
        return True

    @callback(
        Output(DashID.tab4_rapid_res.name, "children"),
        Input(DashID.tab4_rapid_cnf.name, "submit_n_clicks"),
        State(DashID.tab4_rapid_tag.name, "value"),
        State(DashID.tab4_rapid_dur.name, "value"),
        prevent_initial_call=True,
    )
    def callback_tab4_start_measurement(confirm_n_clicks, tag, dur):
        print(confirm_n_clicks, tag, dur)
        tmp_tag = tag if isinstance(tag, str) else "tmp_tag"
        tmp_dur = dur if isinstance(dur, float) or isinstance(dur, int) else 10
        queue_cmd.put((CmdType.start_uav_measurement, [tmp_tag, tmp_dur]))
        return ""

    @callback(
        Output(component_id=DashID.tab4_rapid_prg.name, component_property="value"),
        Output(component_id=DashID.tab4_rapid_prg.name, component_property="label"),
        Input(component_id=DashID.tab4_rapid_liv.name, component_property="n_intervals"),
        prevent_initial_call=True,
    )
    def callback_tab4_live_interval(n):  # -> tuple[float, str]:
        res = 0
        try:
            res = queue_rapid_progress.get_nowait() * 100
            #print(f"{res:.2f}%")
            return res, f"{res:.0f} %" if res >= 5 else ""
        except Exception:
            #print(f"issue with {e}")
            raise PreventUpdate


if __name__ == "__main__":
    dash_thread = DashAppThread(daemon=True)
    ctrl_thread = HardwareCtlThread(daemon=False)

    dash_thread.start()
    ctrl_thread.start()

    ctrl_thread.join()
