import xmlrpc.client
from homematic_connection import EventServer, find_thermostats
from homekit_bridge import ThermoBridge

if __name__ == '__main__':
    client = xmlrpc.client.ServerProxy('http://192.168.178.29:9292/groups')
    server = EventServer(client)

    bridge = ThermoBridge('HomeMatic')

    ths = list(find_thermostats(client, server))
    hk_ths = []
    for th in ths:
        th.poll()
        hk_th = bridge.add_thermostat(th.get_name())
        hk_ths += [ hk_th ]

        def build_update(hk, hm):
            def update():
                hk.current_temp = hm.get_current_temp()
                hk.target_temp = hm.get_target_temp()
                hk.target_hcs = hm.get_homekit_mode()
                hk.set_current_hcs()
                hk.damage()
            return update
        th.on_update(build_update(hk_th, th))

        def build_update2(hm, hk):
            def update():
                hm.set_from_homekit(hk.target_hcs, hk.target_temp)
            return update
        hk_th.on_update(build_update2(th, hk_th))
    print("Found thermostats: %s" % ths)

    print("Starting event server...")
    server.start()

    print("Starting HomeKit bridge...")
    bridge.start()

