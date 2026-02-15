from netfilterqueue import NetfilterQueue
from scapy.all import *

def modify(pkt):
    packet = IP(pkt.get_payload())

    print(packet)

    # Modify
    packet.ttl = 99

    # Recompute checksum
    del packet[IP].chksum
    if packet.haslayer(TCP):
        del packet[TCP].chksum
    if packet.haslayer(UDP):
        del packet[UDP].chksum

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
