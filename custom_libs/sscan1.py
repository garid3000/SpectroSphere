from typing import Tuple
import sys
import time
import serial


class Sscan:
    dbg: bool = True
    ser: serial.Serial

    def __init__(self, devname: str, baudrate: int = 9600,
                 timeout: float = 0.02) -> None:
        """Initialize the object."""
        # self.dbg = True
        self.ser = serial.Serial(devname, baudrate=baudrate, timeout=timeout)

    def set_pos(self, d1: int, d2: int) -> None:
        """Sets current position to d1, d2."""
        self.set_pos_deg(1, d1)
        self.set_pos_deg(2, d2)

    def get_pos(self) -> None:
        """prints current positions in deg."""
        print("pos:", self.get_pos_deg(1), self.get_pos_deg(2))

    def goto(self, d1: int, d2: int, wait: bool = False) -> None:
        """Move motor to d1, d2 degree position."""
        self.ax1_goto(d1)
        self.ax2_goto(d2)

        if wait:
            self.wait2stop(1)
            self.wait2stop(2)

    def ax1_goto(self, degree: float, wait: bool = False) -> None:
        """Set ax1's target position and go to position."""
        self.stop(1)
        fut_pos: int = self.deg2step(degree)
        cur_pos = self.inq_pos(1)
        self.set_motion_mode(1, fut_pos < cur_pos)
        self.set_target_deg(1, degree)
        self.start(1)

        if wait:
            self.wait2stop(1)

    def ax2_goto(self, degree: float, wait: bool = False) -> None:
        """Set ax2's target position and go to position."""
        self.stop(2)
        fut_pos = self.deg2step(degree)
        cur_pos = self.inq_pos(2)
        self.set_motion_mode(2, fut_pos < cur_pos)
        self.set_target_deg(2, degree)
        self.start(2)
        if wait:
            self.wait2stop(2)

    def set_target_deg(self, axis: int, deg: float) -> None:
        """"""
        hexval = self.deg2step(deg)
        ihexval = self.invertHex(hexval)
        print("S{}{:06X}".format(axis, ihexval))
        self.send("S{}{:06X}".format(axis, ihexval))

    def set_pos_deg(self, axis: int, deg: int) -> None:
        hexval: int = self.deg2step(deg)
        ihexval = self.invertHex(hexval)
        # print("E{}{:06X}".format(axis, ihexval))
        self.send("E{}{:06X}".format(axis, ihexval))

    def invertHex(self, hexval: int) -> int:
        newhex = (hexval & (0xFF)) << 16
        newhex |= (hexval & (0xFF << 8))
        newhex |= (hexval & (0xFF << 16)) >> 16
        # print("inv {:06X}".format(newhex))
        # print("act {:06X}".format(hexval))
        return newhex

    def set_motion_mode(self, axis: int, cw: bool) -> None:
        self.wait2stop(axis)
        if cw:
            self.send("G{}01".format(axis))
            print("G{}01".format(axis))
        else:
            self.send("G{}00".format(axis))
            print("G{}00".format(axis))

    def get_pos_deg(self, axis: int) -> float:
        return self.step2deg(self.inq_pos(axis))

    def get_target_deg(self, axis: int) -> float:
        return self.step2deg(self.inq_target(axis))

    def inq_pos(self, axis: int) -> int:
        _, val = self.send('j{}'.format(axis))
        return val - 0x800000

    def inq_target(self, axis: int) -> int:
        _, val = self.send('h{}'.format(axis))
        return val - 0x800000

    def deg2step(self, degree: float) -> int:
        return int(degree*0x1FA400/360) + 0x800000

    def step2deg(self, step) -> float:
        return step/0x1FA400*360

    def stop(self, axis: int = 3, wait: bool = False) -> None:
        self.send('K{}'.format(axis))
        if wait:
            self.wait2stop(1)
            self.wait2stop(2)

    def start(self, axis: int = 3, wait: bool = False) -> None:
        self.send('J{}'.format(axis))
        if wait:
            self.wait2stop(1)
            self.wait2stop(2)

    def wait2stop(self, axis: int, delay: float = .5) -> None:
        while 1:
            if self.isStopped(axis):
                break
            time.sleep(delay)

    def isStopped(self, axis: int) -> bool:
        self.ser.reset_input_buffer()
        self.ser.write(':f{}\r'.format(axis).encode())
        success = self.ser.read(1)
        val = 0
        # print(success)
        if success == b'=':
            _count_ = 0
            while 1:
                retchar = self.ser.read(1)
                # print(retchar, type(retchar), "{:X}".format(val))
                if retchar == b'\r':
                    return False

                if retchar in b"1234567890ABCDEFabcdef":
                    val |= (int(retchar, 16) << _count_ * 4)
                    if _count_ == 1:
                        if int(retchar, 16) % 2 == 0:
                            return True

                else:
                    pass
                    # wrongcharflag = False
                _count_ += 1
        else:
            return False

    def send(self, cmd: str, retsize: int = 1) -> Tuple[bool, int]:
        seq = [1, 0, 3, 2, 5, 4]
        self.ser.reset_input_buffer()
        self.ser.write(':{}\r'.format(cmd).encode())
        success = self.ser.read(1)
        val: int = 0
        # print(success)
        if success == b'=':
            _count_ = 0
            while 1:
                retchar = self.ser.read(1)
                # print(retchar, type(retchar), "{:X}".format(val))
                if retchar == b'\r':
                    return (True, val)
                    # break

                if retchar in b"1234567890ABCDEFabcdef":
                    val |= (int(retchar, 16) << seq[_count_] * 4)
                # else:
                #     wrongcharflag = True
                _count_ += 1
        else:
            print('some error', val, success)
            return (False, 0)


if __name__ == '__main__':
    s = Sscan('/dev/ttyUSB0', baudrate=9600, timeout=0.02)
    sys.exit()