from uasyncio import sleep
from network import WLAN, STA_IF
from config import wifi_ssid, wifi_pswd, wifi_hostname


async def connect_to_wifi(ssid = wifi_ssid, pswd = wifi_pswd, hostname = wifi_hostname):
    """
    Connects to wifi network.
    """
    wlan = WLAN(STA_IF)

    # Creating wlan connection
    print('connecting to wifi: ', ssid)
    wlan.active(True)
    # Disable power-save mode, (and set hostname hostname=hostname, when it will work :()
    wlan.config(pm = 0xa11140)
    wlan.connect(ssid, pswd)

    # Wait for connect or fail
    wait = 20
    while wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        wait -= 1
        await sleep(2)

    if wlan.status() != 3:
        raise RuntimeError('wifi connection failed', wlan.status())
    else:
        print('wifi connected')
        print(wlan.ifconfig())
        return wlan.ifconfig()[0]
