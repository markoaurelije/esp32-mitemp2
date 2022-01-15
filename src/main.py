import os
import json
from my.ledmatrix import LedMatrix

color = (0x07,0x0A,0x10)
led_panel_width = 8
led_panel_height = 7
led_panel_cascades = 3

if 'config.json' in os.listdir():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        for param, value in config.items():
            globals()[param] = value
    except:
        pass
    

led = LedMatrix(led_panel_width, led_panel_height, led_panel_cascades)
led.center_text = True
led.clear(color)
led.clear()

one_hour_cnt = 0
PERIOD = 15000  # 15 seconds
ONE_HOUR = 60*60*1000 / PERIOD

import ntptime
import machine
import utime
import urequests
import ure
import dht
import micropython
from ble_mi2 import get_sensor_data

def getHumidity():
    r = urequests.get("http://vinbit.eu/marvin/?loc=Spansko&sens=Humidity")
    res = r.text
    r.close()
    # res = ure.sub("[^0-9]", "", res)    # remove all non-digit characters
    res = ure.search("[-+]?[0-9]*\.?[0-9]+", res)  # search for float
    if res:
        res = res.group(0)
    return res

def settime():
    t = ntptime.time()
    t += 3600

    time_diff = abs(t - utime.time())
    sync_time = 0
    if time_diff >= 60:
        sync_time = 1
        tm = utime.localtime(t)
        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

        if (machine.RTC().datetime()[6] % PERIOD) > 0:
            initTimer()
            
    r = urequests.get("http://vinbit.eu/marvin/?id={}&d={}&s={}".format(18, time_diff, sync_time))
    res = r.text
    r.close()

def showTime(timer):
    try:
        global led, one_hour_cnt
        one_hour_cnt += 1
        if one_hour_cnt >= ONE_HOUR:
            one_hour_cnt = 0
            settime()
        # if one_hour_cnt % 4 == 0:
        #     hum = getHumidity()
        #     hum = "{} rh".format(hum)
        #     # print(hum)
        #     led.text(hum, color)
        #     print(readDH())
        #     return
        _, _, _, _, h, m, _, _ = machine.RTC().datetime()
        time = '{:d}:{:02d}'.format(h,m)
        led.text(time, color)
        # print(time)
    except:
        print("Exception occured, reseting...")
        machine.reset()

def readDH(pin=2, type=11):
    if type == 11:
        d = dht.DHT11(machine.Pin(pin))
    else:
        d = dht.DHT22(machine.Pin(pin))
    d.measure()
    return ("{} °C".format(d.temperature()), "{} rh".format(d.humidity()))

def initTimer():
    def initTimerPeriodic(timer):
        timer.deinit()
        timer.init(period=PERIOD, mode=machine.Timer.PERIODIC, callback=showTime)
        
    timer.deinit()
    timer.init(period=PERIOD-(machine.RTC().datetime()[6])%PERIOD, mode=machine.Timer.ONE_SHOT, callback=initTimerPeriodic)


timer = machine.Timer(0)

settime()
showTime(None)

if (machine.RTC().datetime()[6]) % PERIOD > 0:
    # debug = "Sleeping {} seconds".format(PERIOD - machine.RTC().datetime()[6])
    # utime.sleep(PERIOD - (machine.RTC().datetime()[6])%PERIOD)
    initTimer()

def upload_sensor_data(sens):
    if sens:
        r = urequests.get("http://vinbit.eu//observe/push/dev-21/s0-tempsens/t0-{0}/s1-vlagasens/t1-{1}/s2-battsens/t2-{2}".format(*sens))
        res = r.text
        r.close()

def cb(*args, **kwargs):
    get_sensor_data(mac=b'\xa4\xc18\x82Y\xdf', callback=upload_sensor_data)

timer2 = machine.Timer(2)
timer2.init(period=1000*60*5, callback=cb)
