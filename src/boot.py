# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
webrepl.start()

import gc
gc.collect()

# import apa102, machine
# strip = apa102.APA102(machine.Pin(5), machine.Pin(4), 8*7*3)
# strip.write()

# del strip
gc.collect()

def do_connect():
    import network
    sta_if = network.WLAN(network.STA_IF)
    if sta_if.isconnected():
        print('Already connected')
    else:
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('B.net_09654', 'y990m32l99d6')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())

    # ap_if = network.WLAN(network.AP_IF)
    # print('AP config:', ap_if.ifconfig())

do_connect()
