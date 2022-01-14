# This example finds and connects to a BLE temperature sensor (e.g. the one in ble_temperature.py).

import bluetooth
import random
import struct
import time
import micropython
from binascii import hexlify

from micropython import const
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_MTU_EXCHANGED = const(21)
_IRQ_L2CAP_ACCEPT = const(22)
_IRQ_L2CAP_CONNECT = const(23)
_IRQ_L2CAP_DISCONNECT = const(24)
_IRQ_L2CAP_RECV = const(25)
_IRQ_L2CAP_SEND_READY = const(26)
_IRQ_CONNECTION_UPDATE = const(27)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)
_IRQ_ALL = const(0xffff)

# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.temperature
_TEMP_UUID = bluetooth.UUID(0x2A6E)
_TEMP_CHAR = (_TEMP_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,)
_ENV_SENSE_SERVICE = (_ENV_SENSE_UUID, (_TEMP_CHAR,),)
_GENERIC_SERIVCE = bluetooth.UUID(0x1800)
_GENERIC_ATTRIBUTE = bluetooth.UUID(0x1801)
_DEVICE_INFORMATION = bluetooth.UUID(0x180a)
_BATTERY_SERIVCE = bluetooth.UUID(0x180f)
_XIAOMI_SERIVE = bluetooth.UUID(0xfe95)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)

# Advertising payloads are repeated packets of the following form:
#   1 byte data length (N + 1)
#   1 byte type (see constants below)
#   N bytes type-specific data
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)


def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            return payload[i + 2:i + payload[i] + 1]
            # result.append(payload[i + 2:i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME)
    return n.decode('utf-8') if n else ''


class BLETemperatureCentral:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
        self._scan_callback = None
        self._conn_callback = None
        self._read_callback = None
        self._write_callback = None
        self._service_done_callback = None
        self._char_done_callback = None

        # Persistent callback for when new data is notified from the device.
        self._notify_callback = None

        # Connected device.
        self._conn_handle = None
        self._value_handle = None

        self.requested_service = bluetooth.UUID(0x2a00)
        self.requested_mac = None

    def _irq(self, event, data):
        # print(event, data)
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, connectable, rssi, adv_data = data
            name = decode_name(bytes(adv_data))
            # print(addr_type, bytes(addr), connectable, hexlify(bytes(
            #     adv_data), ' '), ' > {0}'.format(name) if name else '')
            # if connectable and _ENV_SENSE_UUID in decode_services(adv_data):
            if bytes(addr) == self.requested_mac:
                # print(" Found device, stop scanning.")
                self._addr_type = addr_type
                # Note: The addr buffer is owned by modbluetooth, need to copy it.
                self._addr = bytes(addr)
                self._name = name or '?'
                self._ble.gap_scan(None)

        elif event == _IRQ_SCAN_DONE:
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(
                        self._addr_type, self._addr, self._name)
                    self._scan_callback = None
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # print("Connect successful.")
            conn_handle, addr_type, addr, = data
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
            if self._conn_callback:
                self._conn_callback(addr)
                # self._ble.gattc_discover_services(self._conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # print('Disconnected')
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _, = data
            # print(conn_handle, self._conn_handle)
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # print("Connected device returned a service.")
            conn_handle, start_handle, end_handle, uuid = data
            # if conn_handle == self._conn_handle and uuid == _GENERIC_SERIVCE:
            #     # print("gattc_discover_characteristics", uuid)
            #     self._ble.gattc_discover_characteristics(self._conn_handle, start_handle, end_handle)

        elif event == _IRQ_GATTC_SERVICE_DONE:
            conn_handle, dummy = data
            if conn_handle == self._conn_handle:
                # self._ble.gattc_discover_characteristics(self._conn_handle, 1, 0xffff)
                if self._service_done_callback:
                    self._service_done_callback()

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # print("Connected device returned a characteristic.")
            conn_handle, def_handle, value_handle, properties, uuid = data
            if conn_handle == self._conn_handle and uuid == self.requested_service:
                # print("value handle for", uuid)
                self._value_handle = value_handle

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # We've finished connecting and discovering device, fire the callback.
            if self._char_done_callback:
                self._char_done_callback()

        elif event == _IRQ_GATTC_READ_RESULT:
            # A read completed successfully.
            conn_handle, value_handle, char_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                if self._read_callback:
                    self._read_callback(bytes(char_data))
                    # self._read_callback = None

        elif event == _IRQ_GATTC_WRITE_DONE:
            if self._write_callback:
                self._write_callback()

        elif event == _IRQ_GATTC_NOTIFY:
            # The ble_temperature.py demo periodically notifies its value.
            conn_handle, value_handle, notify_data = data
            if conn_handle == self._conn_handle:
                if self._notify_callback:
                    self._notify_callback(bytes(notify_data))

    # Returns true if we've successfully connected

    def is_connected(self):
        return self._conn_handle is not None

    # Find a device advertising the environmental sensor service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._scan_callback = callback
        # self._ble.gap_scan(2000, 30000, 30000)
        self._ble.gap_scan(10000, 30000, 30000, True)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, callback=None):
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        self._conn_callback = callback
        if self._addr_type is None or self._addr is None:
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        if self._conn_handle is None:
            return
        self._ble.gap_disconnect(self._conn_handle)

    # Issues an (asynchronous) read, will invoke callback with data.
    def read(self, callback):
        if not self.is_connected():
            return
        self._read_callback = callback
        self._ble.gattc_read(self._conn_handle, self._value_handle)

    # Sets a callback to be invoked when the device notifies us.
    def on_notify(self, callback):
        self._notify_callback = callback

    def enable_notifications(self, callback=None):
        self.write(0x38, struct.pack('h', 0x100))
        self._write_callback = callback

    def disable_notifications(self, callback=None):
        self.write(0x38, struct.pack('h', 0x00))
        self._write_callback = callback

    def write(self, handle, value, notify=False):
        # Write the local value, ready for a central to read.
        # print("Writing:", handle, value)
        try:
            self._ble.gattc_write(self._conn_handle, handle, value, 1)
        except Exception as ex:
            print(ex)
        if notify:
            for conn_handle in self._connections:
                # Notify connected centrals to issue a read.
                self._ble.gatts_notify(conn_handle, self._handle)


def get_sensor_data(mac=b'\xa4\xc18\x82Y\xdf'):
    ble = bluetooth.BLE()
    central = BLETemperatureCentral(ble)
    central.requested_mac = mac
    not_found = False
    sensor_data = None

    def on_mi_data_rx(data):
        # print(hexlify(data, '-'))
        temperature = (data[0] + data[1]*255) / 100
        humidity = data[2]
        battery = (data[3] + data[4]*255) / 1000
        print('Temp: ', temperature, "°C")
        print('Hum: ', humidity, "%")
        print('Batt: ', battery, "V")
        nonlocal sensor_data 
        sensor_data = (temperature, humidity, battery)
        central.disable_notifications(central.disconnect)

    def on_scan(addr_type, addr, name):
        if addr_type is not None:
            print('Found sensor:', hexlify(addr, ':'), name)
            central.connect()
        else:
            nonlocal not_found
            not_found = True
            print('No sensor found.')

    central.scan(callback=on_scan)

    central.on_notify(on_mi_data_rx)

    # Wait for connection...
    i = 0
    while not central.is_connected():
        time.sleep_ms(100)
        i += 1
        if i > 100:
            print("Timeout")
            return
        if not_found:
            return

    # print('Connected')
    central.enable_notifications()

    i = 0
    while not sensor_data or central.is_connected():
        time.sleep_ms(100)
        i += 1
        if i > 100:
            print("Timeout")
            return sensor_data

    return sensor_data


def scan_for_sensors():
    return
