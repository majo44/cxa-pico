# The code taken from https://github.com/peterhinch/micropython_ir
#
# MIT License
#
# Copyright (c) 2020 Peter Hinch
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Thanks to Peter Hinch

import rp2
from machine import Pin, PWM
from micropython import const
from array import array
from time import ticks_us, ticks_diff, sleep_ms, sleep

from config import ir_pin, verbose

# Philips RC5 protocol
_T_RC5 = const(889)  # Time for pulse of carrier
STOP = const(0)  # End of data

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, autopull=True, pull_thresh=32)
def pulsetrain():
    wrap_target()
    out(x, 32)  # No of 1MHz ticks. Block if FIFO MT at end.
    irq(rel(0))
    set(pins, 1)  # Set pin high
    label('loop')
    jmp(x_dec,'loop')
    irq(rel(0))
    set(pins, 0)  # Set pin low
    out(y, 32)  # Low time.
    label('loop_lo')
    jmp(y_dec,'loop_lo')
    wrap()


class RP2_RMT:

    def __init__(self, pin_pulse, carrier, sm_no=0, sm_freq=1_000_000):
        pin_car, freq, duty = carrier
        self.pwm = PWM(pin_car)  # Set up PWM with carrier off.
        self.pwm.freq(freq)
        self.pwm.duty_u16(0)
        self.duty = (int(0xffff * duty // 100), 0)
        self.sm = rp2.StateMachine(sm_no, pulsetrain, freq=sm_freq, set_base=pin_pulse)
        self.apt = 0  # Array index
        self.arr = None  # Array
        self.ict = None  # Current IRQ count
        self.icm = 0  # End IRQ count
        self.reps = 0  # 0 == forever n == no. of reps
        rp2.PIO(0).irq(self._cb)

    # IRQ callback. Because of FIFO IRQ's keep arriving after STOP.
    def _cb(self, pio):
        self.pwm.duty_u16(self.duty[self.ict & 1])
        self.ict += 1
        if d := self.arr[self.apt]:  # If data available feed FIFO
            self.sm.put(d)
            self.apt += 1
        else:
            if r := self.reps != 1:  # All done if reps == 1
                if r:  # 0 == run forever
                    self.reps -= 1
                self.sm.put(self.arr[0])
                self.apt = 1  # Set pointer and count to state
                self.ict = 1  # after 1st IRQ

    # Arg is an array of times in μs terminated by 0.
    def send(self, ar, reps=1, check=True):
        self.sm.active(0)
        self.reps = reps
        ar[-1] = 0  # Ensure at least one STOP
        for x, d in enumerate(ar):  # Find 1st STOP
            if d == 0:
                break
        if check:
            # Pulse train must end with a space otherwise we leave carrier on.
            # So, if it ends with a mark, append a space. Note __init__.py
            # ensures that there is room in array.
            if (x & 1):
                ar[x] = 1  # space. Duration doesn't matter.
                x += 1
                ar[x] = 0  # STOP
        self.icm = x  # index of 1st STOP
        mv = memoryview(ar)
        n = min(x, 4)  # Fill FIFO if there are enough data points.
        self.sm.put(mv[0 : n])
        self.arr = ar  # Initial conditions for ISR
        self.apt = n  # Point to next data value
        self.ict = 0  # IRQ count
        self.sm.active(1)

    def busy(self):
        if self.ict is None:
            return False  # Just instantiated
        return self.ict < self.icm

    def cancel(self):
        self.reps = 1


# IR abstract base class. Array holds periods in μs between toggling 36/38KHz
# carrier on or off. Physical transmission occurs in an ISR context controlled
# by timer 2 and timer 5. See TRANSMITTER.md for details of operation.
class IR:
    _active_high = True  # Hardware turns IRLED on if pin goes high.
    _space = 0  # Duty ratio that causes IRLED to be off
    timeit = False  # Print timing info

    @classmethod
    def active_low(cls):
        cls._active_high = False
        cls._space = 100

    def __init__(self, pin, cfreq, asize, duty, verbose):
        self._rmt = RP2_RMT(pin_pulse=None, carrier=(pin, cfreq, duty))  # 1μs resolution
        asize += 1  # Allow for possible extra space pulse
        self._tcb = self._cb  # Pre-allocate
        self._arr = array('H', 0 for _ in range(asize))  # on/off times (μs)
        self._mva = memoryview(self._arr)
        # Subclass interface
        self.verbose = verbose
        self.carrier = False  # Notional carrier state while encoding biphase
        self.aptr = 0  # Index into array

    def _cb(self, t):  # T5 callback, generate a carrier mark or space
        t.deinit()
        p = self.aptr
        v = self._arr[p]
        if v == STOP:
            self._ch.pulse_width_percent(self._space)  # Turn off IR LED.
            return
        self._ch.pulse_width_percent(self._space if p & 1 else self._duty)
        self._tim.init(prescaler=84, period=v, callback=self._tcb)
        self.aptr += 1

    # Public interface
    # Before populating array, zero pointer, set notional carrier state (off).
    def transmit(self, addr, data, toggle=0):
        t = ticks_us()
        self.aptr = 0  # Inital conditions for tx: index into array
        self.carrier = False
        self.tx(addr, data, toggle)  # Subclass populates ._arr
        self.trigger()  # Initiate transmission
        if self.timeit:
            dt = ticks_diff(ticks_us(), t)
            print('ir time = {}μs'.format(dt))

    # Subclass interface
    def trigger(self):  # Used by NEC to initiate a repeat frame
        self.append(STOP)
        self._rmt.send(self._arr)

    def append(self, *times):  # Append one or more time peiods to ._arr
        for t in times:
            self._arr[self.aptr] = t
            self.aptr += 1
            self.carrier = not self.carrier  # Keep track of carrier state
            self.verbose and print('ir append', t, 'carrier', self.carrier)

    def add(self, t):  # Increase last time value (for biphase)
        assert t > 0
        self.verbose and print('ir add', t)
        # .carrier unaffected
        self._arr[self.aptr - 1] += t


class RC5(IR):
    """
    The RC5 ir protocol implementation
    """
    valid = (0x1f, 0x7f, 1)  # Max addr, data, toggle
    last_toggle = 0

    def __init__(self, pin = ir_pin, verbose = verbose):
        super().__init__(Pin(pin, Pin.OUT, value = 0), 36000, 28, 30, verbose)
        self.timeit = verbose

    def tx(self, addr, data, toggle):  # Fix RC5X S2 bit polarity
        d = (data & 0x3f) | ((addr & 0x1f) << 6) | (((data & 0x40) ^ 0x40) << 6) | ((toggle & 1) << 11)
        self.verbose and print('ir ', bin(d))
        mask = 0x2000
        while mask:
            if mask == 0x2000:
                self.append(_T_RC5)
            else:
                bit = bool(d & mask)
                if bit ^ self.carrier:
                    self.add(_T_RC5)
                    self.append(_T_RC5)
                else:
                    self.append(_T_RC5, _T_RC5)
            mask >>= 1

    def v_up(self):
        self.transmit(16, 16)
        sleep_ms(80)

    def v_down(self):
        self.transmit(16, 17)
        sleep_ms(80)
