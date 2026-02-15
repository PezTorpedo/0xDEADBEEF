from netfilterqueue import NetfilterQueue
from scapy.all import *

def modify(pkt):
    packet = IP(pkt.get_payload())
    print(packet)

    client = "192.168.10.10"
    whitelisted_servers = ["192.168.10.1", "34.117.13.189"]

    # MH ["192.168.10.1", "46.51.188.91", "34.90.173.67", "34.117.13.189"]
    # NO ["192.168.10.1", "34.117.13.189"]

    if not ((packet.src == client and packet.dst in whitelisted_servers) or
        (packet.src in whitelisted_servers and packet.dst == client)):
        pkt.drop()
        return

    print(packet)

    # Re-inject
    pkt.set_payload(bytes(packet))
    pkt.accept()

nfq = NetfilterQueue()
nfq.bind(0, modify)

try:
    print("Queue activated. CTRL+C to exit.")
    nfq.run()
except KeyboardInterrupt:
    print("Stopped")
