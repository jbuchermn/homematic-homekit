from threading import Thread
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

OFF_VALUE = 4.5

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    res = s.getsockname()[0]
    s.close()
    return res

class EventServer(Thread):
    def __init__(self, client):
        super().__init__()
        self._client = client
        self._ip = get_ip()

        self._thermostats = {}

    def _on_event(self, id, address, key, value):
        if address in self._thermostats:
            th = self._thermostats[address]
            th.update(None if key != 'CONTROL_MODE' else value,
                      None if key != 'SET_TEMPERATURE' else value,
                      None if key != 'ACTUAL_TEMPERATURE' else value)

    def register(self, address, th):
        self._thermostats[address] = th

    def run(self):
        print("Registering server...")
        self._client.init("http://%s:9293" % self._ip, "my-id")
        print("...done")

        print("Starting XML-RPC server on http://%s:9293..." % self._ip)
        server = SimpleXMLRPCServer(('0.0.0.0', 9293))
        server.register_introspection_functions()
        server.register_function(self._on_event, "event")

        try:
            server.serve_forever()
        finally:
            print("Unregistering server...")
            client.init("http://%s:9293" % self._ip, "")
            print("...done")


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
        state = self._client.getParamset(self._address, "VALUES")
        self._mode = state['CONTROL_MODE']
        self._target_temp = state['SET_TEMPERATURE']
        self._current_temp = state['ACTUAL_TEMPERATURE']
        self.update(None, None, None)

    def update(self, mode, target_temp, current_temp):
        if mode is not None:
            self._mode = mode
        if target_temp is not None:
            self._target_temp = target_temp
        if current_temp is not None:
            self._current_temp = current_temp

        for c in self._callbacks:
            c()

    def set(self, mode, target_temp):
        self._client.setValue(self._address, "SET_TEMPERATURE", target_temp)
        self._client.setValue(self._address, "CONTROL_MODE", mode)
        self.poll()

    def get_homekit_mode(self):
        if abs(self._target_temp - OFF_VALUE) < 0.1:
            return HOMEKIT_HCS_OFF
        elif self._mode == HOMEMATIC_MODE_AUTO:
            return HOMEKIT_HCS_AUTO
        elif self._mode == HOMEMATIC_MODE_MANU:
            return HOMEKIT_HCS_HEATING
        else:
            return HOMEKIT_HCS_COOLING

    def set_from_homekit(self, homekit_mode, target_temp):
        print("SETTING FROM: %d %f" % (homekit_mode, target_temp))
        mode = self._mode
        temp = target_temp
        if self.get_homekit_mode() != homekit_mode:
            if homekit_mode == HOMEKIT_HCS_OFF:
                mode = HOMEMATIC_MODE_AUTO
                temp = OFF_VALUE
            elif homekit_mode == HOMEKIT_HCS_AUTO:
                mode = HOMEMATIC_MODE_AUTO
                if abs(temp - OFF_VALUE) < 0.1:
                    temp = 22.0
            elif homekit_mode == HOMEKIT_HCS_HEATING:
                mode = HOMEMATIC_MODE_MANU
                if abs(temp - OFF_VALUE) < 0.1:
                    temp = 22.0
            elif homekit_mode == HOMEKIT_HCS_COOLING:
                mode = HOMEMATIC_MODE_BOOST
                if abs(temp - OFF_VALUE) < 0.1:
                    temp = 22.0
        print("SETTING: %d %f" % (mode, temp))
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
    print("Found thermostats: %s" % ths)

    server.run()


