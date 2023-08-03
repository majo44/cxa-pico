from uasyncio import sleep_ms
from utime import ticks_ms
from machine import Pin, UART
from config import rs_rx_pin, rs_tx_pin

timeout = 1000
uart = UART(0, baudrate=9600, tx=Pin(rs_tx_pin), rx=Pin(rs_rx_pin))

async def rs_send(message):
    prv_mills = ticks_ms()
    print('rs write', message)
    uart.write(message)
    msg = ''
    start = 0
    while (ticks_ms() - prv_mills) < timeout:
        if uart.any():
            start = 1
            rcv_char = uart.read()
            msg = msg + rcv_char.decode("ascii")
            await sleep_ms(10)
        else:
            if start == 1:
                break
    print('rs read' , msg)
    return msg


async def rs_send_power(value = None):
    if value is None:
        res = await rs_send('#1,01\r')
    elif value:
        res = await rs_send('#1,02,1\r')
    else:
        res = await rs_send('#1,02,0\r')
    return res.find('#02,01,1') > -1


async def rs_send_mute(value = None):
    if value is None:
        res = await rs_send('#1,03\r')
    elif value:
        res = await rs_send('#1,04,1\r')
    else:
        res = await rs_send('#1,04,0\r')
    return res.find('#02,03,1') > -1


async def rs_send_source(value=None):
    if value is None:
        res = await rs_send('#3,01\r')
    else:
        res = await rs_send(f"#3,04,{value}\r")
    if res.find('#04,01,') > -1:
        return res.split(',')[2][0:2]
    else:
        return '-1'

