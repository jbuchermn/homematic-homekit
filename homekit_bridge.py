import signal

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_THERMOSTAT


HOMEKIT_HCS_OFF = 0
HOMEKIT_HCS_HEATING = 1
HOMEKIT_HCS_COOLING = 2
HOMEKIT_HCS_AUTO = 3

class Thermostat(Accessory):
    category = CATEGORY_THERMOSTAT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._callbacks = []
        self._damaged = True

        service = self.add_preload_service('Thermostat')
        service.setter_callback = self._set_chars

        self._current_hcs = service.configure_char('CurrentHeatingCoolingState')
        self._target_hcs = service.configure_char('TargetHeatingCoolingState')
        self._current_temp = service.configure_char('CurrentTemperature')
        self._target_temp = service.configure_char('TargetTemperature')
        self._temp_units = service.configure_char('TemperatureDisplayUnits')

        self.target_temp = 22.0
        self.current_temp = 25.0
        self.target_hcs = 0
        self.current_hcs = 0

    def damage(self):
        self._damaged = True

    def _set_chars(self, char_values):
        if 'TargetTemperature' in char_values:
            self.target_temp = char_values['TargetTemperature']
        if 'TargetHeatingCoolingState' in char_values:
            self.target_hcs = char_values['TargetHeatingCoolingState']

        self.damage()
        for c in self._callbacks:
            c()

    @Accessory.run_at_interval(3)
    async def run(self):
        if not self._damaged:
            return
        self._damaged = False

        self._current_temp.set_value(self.current_temp)
        self._target_temp.set_value(self.target_temp)
        self._current_hcs.set_value(self.current_hcs)
        self._target_hcs.set_value(self.target_hcs)
        self._temp_units.set_value(0.5)

    def on_update(self, callback):
        self._callbacks += [ callback ]

    def set_current_hcs(self):
        if self.target_hcs != HOMEKIT_HCS_OFF:
            self.current_hcs = 1
        else:
            self.current_hcs = 0


class ThermoBridge:
    def __init__(self, name):
        self._driver = AccessoryDriver(port=51826)
        self._bridge = Bridge(self._driver, name)
        self._driver.add_accessory(accessory=self._bridge)

    def add_thermostat(self, name):
        th = Thermostat(self._driver, name)
        self._bridge.add_accessory(th)
        return th

    def start(self):
        signal.signal(signal.SIGTERM, self._driver.signal_handler)
        self._driver.start()


if __name__ == '__main__':
    bridge = ThermoBridge('TestBridge0')

    th1 = bridge.add_thermostat('Wohnzimmer')
    th1.on_update(lambda: print("Update Wohnzimmer"))

    th1.target_temp = 25.0
    th1.damage()

    th2 = bridge.add_thermostat('Bad')
    th2.on_update(lambda: print("Update Bad"))

    th3 = bridge.add_thermostat('Schlafzimmer')
    th3.on_update(lambda: print("Update Schlafzimmer"))

    bridge.start()
