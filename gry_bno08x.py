import sys
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


# data = np.zeros((100, 9))
# 
# for i in range(100):
#     time.sleep(0.1)
#     accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
#     #print("X: %0.6f  Y: %0.6f Z: %0.6f  m/s^2" % (accel_x, accel_y, accel_z), end = '|')
# 
#     gyro_x, gyro_y, gyro_z = bno.gyro  # pylint:disable=no-member
#     #print("X: %0.6f  Y: %0.6f Z: %0.6f rads/s" % (gyro_x, gyro_y, gyro_z), end='|')
# 
#     mag_x, mag_y, mag_z = bno.magnetic  # pylint:disable=no-member
#     #print("X: %0.6f  Y: %0.6f Z: %0.6f uT" % (mag_x, mag_y, mag_z), end='|')
# 
#     data[i,:] = [accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z,mag_x, mag_y, mag_z   ]
#     #if bno.shake:
#     #    print("SHAKE DETECTED!")
#     #print('', end='\r', flush=True)



if __name__ == "__main__":
    cli_args = {
        each_arg.split('=')[0]:each_arg.split('=')[1]
        for each_arg in sys.argv[1:]
        if each_arg.count('=') == 1
    }
    
    
    if "out" in cli_args:
        data = np.zeros((100, 9))

        for i in range(100):
            time.sleep(0.1)
            accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
            #print("X: %0.6f  Y: %0.6f Z: %0.6f  m/s^2" % (accel_x, accel_y, accel_z), end = '|')

            gyro_x, gyro_y, gyro_z = bno.gyro  # pylint:disable=no-member
            #print("X: %0.6f  Y: %0.6f Z: %0.6f rads/s" % (gyro_x, gyro_y, gyro_z), end='|')

            mag_x, mag_y, mag_z = bno.magnetic  # pylint:disable=no-member
            #print("X: %0.6f  Y: %0.6f Z: %0.6f uT" % (mag_x, mag_y, mag_z), end='|')

            data[i,:] = [accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z,mag_x, mag_y, mag_z   ]

        np.save(f"{cli_args['out']}", data)

    elif "show_loop" in cli_args:
        for i in range(int(cli_args["show_loop"])):
            time.sleep(0.1)
            accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
            print(f"X:{accel_x:0.3f} Y:{accel_y:0.3f} Z:{accel_z:0.3f} m/s^2")

    else:
        accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
        print(f"X:{accel_x:0.3f}\nY:{accel_y:0.3f}\nZ:{accel_z:0.3f} m/s^2")
