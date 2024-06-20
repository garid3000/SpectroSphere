import time
import sys
import board
import busio
from adafruit_bno08x.i2c import BNO08X_I2C
from adafruit_bno08x import (
    BNO_REPORT_ACCELEROMETER,
    BNO_REPORT_GYROSCOPE,
    BNO_REPORT_MAGNETOMETER,
    BNO_REPORT_ROTATION_VECTOR,
)
import numpy as np


i2c = busio.I2C(board.SCL, board.SDA)  # , frequency=100000)
bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_ACCELEROMETER)
bno.enable_feature(BNO_REPORT_GYROSCOPE)
bno.enable_feature(BNO_REPORT_MAGNETOMETER)
bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)


if __name__ == "__main__":
    cli_args = {each_arg.split("=")[0]: each_arg.split("=")[1] for each_arg in sys.argv[1:] if each_arg.count("=") == 1}

    if "out" in cli_args:
        data = np.zeros((100, 9))

        for i in range(100):
            time.sleep(0.1)
            acc_x, acc_y, acc_z = bno.acceleration  # pylint:disable=no-member
            gyr_x, gyr_y, gyr_z = bno.gyro  # pylint:disable=no-member
            mag_x, mag_y, mag_z = bno.magnetic  # pylint:disable=no-member
            data[i, :] = [acc_x, acc_y, acc_z, gyr_x, gyr_y, gyr_z, mag_x, mag_y, mag_z]

        np.save(f"{cli_args['out']}", data)

    elif "show_loop" in cli_args:
        for i in range(int(cli_args["show_loop"])):
            time.sleep(0.1)
            acc_x, acc_y, acc_z = bno.acceleration  # pylint:disable=no-member
            print(f"X:{acc_x:0.3f} Y:{acc_y:0.3f} Z:{acc_z:0.3f} m/s^2")

    else:
        while True:
            acc_x, acc_y, acc_z = bno.acceleration  # pylint:disable=no-member
            print("X: %0.6f  Y: %0.6f Z: %0.6f  m/s^2" % (acc_x, acc_y, acc_z), end="\t")

            gyr_x, gyr_y, gyr_z = bno.gyro  # pylint:disable=no-member
            print("X: %0.6f  Y: %0.6f Z: %0.6f  m/s^2" % (gyr_x, gyr_y, gyr_z), end="\t")

            mag_x, mag_y, mag_z = bno.magnetic  # pylint:disable=no-member
            print("X: %0.6f  Y: %0.6f Z: %0.6f  m/s^2" % (mag_x, mag_y, mag_z), end="\t")
            quat_i, quat_j, quat_k, quat_real = bno.quaternion
            print(quat_i, quat_j, quat_k, quat_real)

            time.sleep(0.05)
