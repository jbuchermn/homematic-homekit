import time
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

print("Opening connection...")
s = xmlrpc.client.ServerProxy('http://192.168.178.29:9292/groups')
print("...open")

# print("Server methods:")
# print(s.system.listMethods())
#
print("List all devices:")
print(s.listDevices())

print("Get status:")
print(s.getParamset("INT0000001:1", "VALUES"))

time.sleep(1)

print("Set:")
print(s.setValue("INT0000001:1", "CONTROL_MODE", 0))
print(s.setValue("INT0000001:1", "SET_TEMPERATURE", 4.5))

time.sleep(1)

print("Get status:")
print(s.getParamset("INT0000001:1", "VALUES"))

print("Init...")
s.init("http://192.168.178.67:9293", "my-id")
print("...sent")


def event(*args, **kwargs):
    print("EVENT: %s, %s" % (args, kwargs))

print("Starting XML RPC server")
server = SimpleXMLRPCServer(('0.0.0.0', 9293))
server.register_introspection_functions()
server.register_function(event)

try:
    server.serve_forever()
finally:
    print("Deinit...")
    s.init("http://192.168.178.67:9293", "")
    print("...sent")
