from threading import Thread
import time
import socket
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

from homekit_bridge import HOMEKIT_HCS_OFF, HOMEKIT_HCS_COOLING, HOMEKIT_HCS_HEATING, HOMEKIT_HCS_AUTO

HOMEMATIC_MODE_AUTO = 0
HOMEMATIC_MODE_MANU = 1
HOMEMATIC_MODE_PARTY = 2
HOMEMATIC_MODE_BOOST = 3
HOMEMATIC_MODE_COMFORT = 4
HOMEMATIC_MODE_LOWERING = 5

def print_homematic_mode(val):
    if val == HOMEMATIC_MODE_AUTO:
        return "AUTO"
    elif val == HOMEMATIC_MODE_MANU:
        return "MANU"
    elif val == HOMEMATIC_MODE_PARTY:
        return "PARTY"
    elif val == HOMEMATIC_MODE_BOOST:
        return "BOOST"
    elif val == HOMEMATIC_MODE_COMFORT:
        return "COMFORT"
    elif val == HOMEMATIC_MODE_LOWERING:
        return "LOWERING"
    else:
        return "None"

OFF_VALUE = 4.5

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    res = s.getsockname()[0]
    s.close()
    return res

class EventServer:
    def __init__(self, client, run_poll_server=True, run_xml_server=False):
        self._client = client
        self._ip = get_ip()

        self._run_poll_server = run_poll_server
        self._run_xml_server = run_xml_server

        self._thermostats = {}

    def _on_event(self, id, address, key, value):
        if address in self._thermostats:
            th = self._thermostats[address]
            th.update(None if key != 'CONTROL_MODE' else value,
                      None if key != 'SET_TEMPERATURE' else value,
                      None if key != 'ACTUAL_TEMPERATURE' else value)

    def register(self, address, th):
        self._thermostats[address] = th

    def _run_poll(self):
        while True:
            for v in self._thermostats.values():
                v.poll()
            time.sleep(15)

    def _run_xml(self):
        print("Registering server...")
        self._client.init("http://%s:9293" % self._ip, "my-id")
        print("...done")

        print("Starting XML-RPC server on http://%s:9293..." % self._ip)
        server = SimpleXMLRPCServer(('0.0.0.0', 9293), logRequests=False)
        server.register_introspection_functions()
        server.register_function(self._on_event, "event")

        try:
            server.serve_forever()
        finally:
            print("Unregistering server...")
            client.init("http://%s:9293" % self._ip, "")
            print("...done")

    def start(self):
        if self._run_poll_server:
            Thread(target=self._run_poll).start()
        if self._run_xml_server:
            Thread(target=self._run_xml).start()


class HMThermostat:
    def __init__(self, client, address):
        self._client = client
        self._address = address
        self._callbacks = []

        self._mode = -1
        self._target_temp = 0.0
        self._current_temp = 0.0

    def get_name(self):
        return self._address

    def get_target_temp(self):
        return self._target_temp

    def get_current_temp(self):
        return self._current_temp

    def on_update(self, cb):
        self._callbacks += [ cb ]

    def poll(self):
        try:
            state = self._client.getParamset(self._address, "VALUES")
            self._mode = state['CONTROL_MODE']
            self._target_temp = state['SET_TEMPERATURE']
            self._current_temp = state['ACTUAL_TEMPERATURE']
            print("[%s] <--- Poll" % self._address)
            self.update(None, None, None)

        except Exception as e:
            print(e)

    def update(self, mode, target_temp, current_temp):
        if mode is not None:
            self._mode = mode
        if target_temp is not None:
            self._target_temp = target_temp
        if current_temp is not None:
            self._current_temp = current_temp

        print("[%s] <--- Update: %s %f %f" % (self._address, print_homematic_mode(self._mode), self._target_temp, self._current_temp))
        for c in self._callbacks:
            c()

    def set(self, mode, target_temp):
        try:
            if mode == HOMEMATIC_MODE_AUTO:
                print("[%s] ---> Push: AUTO_MODE" % self._address)
                self._client.setValue(self._address, "AUTO_MODE", True)

            elif mode == HOMEMATIC_MODE_MANU:
                print("[%s] ---> Push: MANU_MODE: %f" % (self._address, target_temp))
                self._client.setValue(self._address, "MANU_MODE", float(target_temp))

            elif mode == HOMEMATIC_MODE_BOOST:
                print("[%s] ---> Push: BOOST_MODE" % self._address)
                self._client.setValue(self._address, "BOOST_MODE", True)

        except Exception as e:
            print(e)

        time.sleep(.5)
        self.poll()

    def get_homekit_mode(self):
        if abs(self._target_temp - OFF_VALUE) < 0.1:
            if self._mode == HOMEMATIC_MODE_MANU:
                return HOMEKIT_HCS_OFF
        
        if self._mode == HOMEMATIC_MODE_AUTO:
            return HOMEKIT_HCS_AUTO
        elif self._mode == HOMEMATIC_MODE_MANU:
            return HOMEKIT_HCS_HEATING
        else:
            return HOMEKIT_HCS_COOLING

    def set_from_homekit(self, homekit_mode, target_temp):
        mode = self._mode
        temp = target_temp
        if self.get_homekit_mode() != homekit_mode:
            if homekit_mode == HOMEKIT_HCS_OFF:
                mode = HOMEMATIC_MODE_MANU
                temp = OFF_VALUE
            elif homekit_mode == HOMEKIT_HCS_AUTO:
                mode = HOMEMATIC_MODE_AUTO
                if abs(temp - OFF_VALUE) < 0.1:
                    temp = 17.0
            elif homekit_mode == HOMEKIT_HCS_HEATING:
                mode = HOMEMATIC_MODE_MANU
                if abs(temp - OFF_VALUE) < 0.1:
                    temp = 17.0
            elif homekit_mode == HOMEKIT_HCS_COOLING:
                mode = HOMEMATIC_MODE_BOOST
                if abs(temp - OFF_VALUE) < 0.1:
                    temp = 17.0
        self.set(mode, temp)

    def __repr__(self):
        return "HMThermostat(%s) at %fC, t=%fC (%d)" % (self._address, self._current_temp, self._target_temp, self._mode)

def find_thermostats(client, server):
    devs = client.listDevices()
    for d in devs:
        if d['TYPE'] == "CLIMATECONTROL_RT_TRANSCEIVER":
            th = HMThermostat(client, d['ADDRESS'])
            server.register(d['ADDRESS'], th)
            yield th

if __name__ == '__main__':
    print("Opening connection...")
    client = xmlrpc.client.ServerProxy('http://192.168.178.29:9292/groups')
    print("...open")

    server = EventServer(client)

    ths = list(find_thermostats(client, server))
    for th in ths:
        th.poll()
        th.set(HOMEMATIC_MODE_MANU, OFF_VALUE)
    print("Found thermostats: %s" % ths)

    # server.start()


