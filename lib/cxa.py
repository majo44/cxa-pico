from uasyncio import sleep, run, new_event_loop, create_task
from server import server_start
from wifi import connect_to_wifi
from machine import Pin, WDT
from socket import socket, getaddrinfo
from config import wdt_enabled, wdt_url

async def main():
    led = Pin("LED", Pin.OUT, value=0)
    await connect_to_wifi()
    await create_task(server_start())

    # Blinking led on restart
    led.on()
    await sleep(0.25)
    led.off()
    await sleep(0.25)
    led.on()
    await sleep(0.25)
    led.off()

    cycle = 0
    wdt = None
    if wdt_enabled:
        wdt = WDT(timeout=8000)

    while True:
        if wdt_enabled:
            if cycle == 0:
                try:
                    print('checking')
                    a = getaddrinfo(wdt_url, 80)[0][-1]
                    s = socket()
                    s.connect(a)
                    s.send(b"GET / HTTP/1.0\r\n\r\n")
                    data = str(s.recv(4), 'utf8')
                    if data == 'HTTP':
                        s.close()
                    wdt.feed()
                except:
                    pass
                cycle = 20
            else:
                wdt.feed()
                cycle = cycle - 1
        await sleep(4)

try:
    run(main())
finally:
    new_event_loop()
