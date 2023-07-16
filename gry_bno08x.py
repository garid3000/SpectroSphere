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


data = np.zeros((100, 9))

# while True:
for i in range(100):
    time.sleep(0.1)

    accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
    gyro_x,  gyro_y,  gyro_z = bno.gyro           # pylint:disable=no-member
    mag_x,   mag_y,   mag_z = bno.magnetic        # pylint:disable=no-member

    print(f"X={accel_x:8.6f} Y={accel_y:8.6x} Z={accel_z:8.6x} |", endl='')
    print(f"X={gyro_x:8.6f}  Y={gyro_y:8.6x}  Z={gyro_z:8.6x}  |", endl='')
    print(f"X={mag_x:8.6f}   Y={mag_y:8.6x}   Z={mag_z:8.6x}   |", endl='')

    data[i, :] = [accel_x, accel_y, accel_z,
                  gyro_x,  gyro_y,  gyro_z,
                  mag_x,   mag_y,   mag_z]
    if bno.shake:
        print("SHAKE DETECTED!")

    print('', end='\r', flush=True)

print()

if input('Do you want to save it? y/n') == 'y':
    np.save('startof/{}'.format(input('name:')), data)
    print('save')
else:
    print('no save')
