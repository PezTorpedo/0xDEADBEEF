from netfilterqueue import NetfilterQueue
from scapy.all import *

def modify(pkt):
    packet = IP(pkt.get_payload())

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
