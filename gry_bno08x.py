from typing import Optional, Tuple

import time
import board
import busio
import adafruit_bno08x
from adafruit_bno08x.i2c import BNO08X_I2C
import numpy as np
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
bno = BNO08X_I2C(i2c)

bno.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_MAGNETOMETER)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_LINEAR_ACCELERATION)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_GAME_ROTATION_VECTOR)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_STEP_COUNTER)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_STABILITY_CLASSIFIER)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_ACTIVITY_CLASSIFIER)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_SHAKE_DETECTOR)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_RAW_ACCELEROMETER)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_RAW_GYROSCOPE)
bno.enable_feature(adafruit_bno08x.BNO_REPORT_RAW_MAGNETOMETER)


data = np.zeros((100, 9), dtype=np.float64)

for i in range(100):
    time.sleep(0.1)

    acc_xyz: Optional[Tuple[float, float, float]] = bno.acceleration
    gyr_xyz: Optional[Tuple[float, float, float]] = bno.gyro
    mag_xyz: Optional[Tuple[float, float, float]] = bno.magnetic

    if acc_xyz is not None:
        print(f"X={acc_xyz[0]:8.6f} Y={acc_xyz[1]:8.6x} Z={acc_xyz[2]:8.6x} |", end='')
        data[i, 0:3] = acc_xyz
    if gyr_xyz is not None:
        print(f"X={gyr_xyz[0]:8.6f} Y={gyr_xyz[1]:8.6x} Z={gyr_xyz[2]:8.6x} |", end='')
        data[i, 3:6] = gyr_xyz
    if mag_xyz is not None:
        print(f"X={mag_xyz[0]:8.6f} Y={mag_xyz[1]:8.6x} Z={mag_xyz[2]:8.6x} |", end='')
        data[i, 6:9] = mag_xyz

    if bno.shake:
        print("SHAKE DETECTED!")

    print('', end='\r', flush=True)

print()

if input('Do you want to save it? y/n') == 'y':
    np.save('startof/{}'.format(input('name:')), data)
    print('save')
else:
    print('no save')
