#!/usr/bin/env python3

# Run using "python3.10 sniffer.py"

from scapy.all import *
from scapy.layers.dot15d4 import *
from killerbee import KillerBee

# 5210 = 0x145a (Philips Hue Bridge)
# 37335 = 0x91d7 (Hue Color Lamp 1)
# 33043 = 0x8113 (Philips Hue Dimmer Switch)

CHANNEL = 11

conf.dot15d4_protocol = "zigbee"

kb = KillerBee()
kb.set_channel(CHANNEL)
kb.sniffer_on()

while True:
    packet_data = kb.pnext()
    if not packet_data:
        continue

    raw_bytes = packet_data["bytes"]
    frame = Dot15d4(raw_bytes)
    frame.show()

    #if ZigbeeNWK in frame:
        #s = frame[ZigbeeNWK].source
        #d = frame[ZigbeeNWK].destination
        #if not ((s == 5210 and d == 37335) or (s == 37335 and d == 5210)):
            #frame.show()