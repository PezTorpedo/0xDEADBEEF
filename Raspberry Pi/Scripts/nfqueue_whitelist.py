from netfilterqueue import NetfilterQueue
from scapy.all import *

def modify(pkt):
    packet = IP(pkt.get_payload())
    print(packet)

    client = "192.168.10.10"
    whitelisted_servers = [
        "192.168.10.1",                   # Gateway
        "192.168.20.50",                  # Computer
        "192.168.20.51",
        #"192.168.20.61",                  # Phone
        
        "52.48.41.28", "46.51.188.91", "99.80.116.23",  # diagnostics.huedatastore.com
        "34.90.173.67",                                 # mqtt-eu-01.iot.meethue.com
        "34.117.13.189"                                 # ws.meethue.com
    ]

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
