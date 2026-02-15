from netfilterqueue import NetfilterQueue
from scapy.all import *

# Could be improved to better manage next frames (packet[TCP].seq + packet[TCP].ack)

carry = b''
addCarryToNextFrame = False

def modify(pkt):
    global carry
    global addCarryToNextFrame

    packet = IP(pkt.get_payload())
    # print(packet.show())

    if packet.haslayer(TCP):
        if packet[TCP].haslayer(Raw):
            data = packet[TCP][Raw].load
            packet_length = len(bytes(packet))  # Max is 1500

            if b"Welcome to hue - your personal wireless lighting system." in data or addCarryToNextFrame:
                if addCarryToNextFrame:
                    data = carry + data
                    caryr = b''
                    addCarryToNextFrame = False

                    content_length_diff = len(carry)
                else:
                    old_string = b"Welcome to hue"
                    new_string = b"Welcome to f***ing hue"
                    data = data.replace(old_string, new_string);

                    old_content_length = int(re.search(rb"Content-Length:\s*(\d+)", data).group(1))
                    content_length_diff = len(new_string) - len(old_string)
                    new_content_length = old_content_length + content_length_diff

                    data = data.replace(f"Content-Length: {old_content_length}".encode(), f"Content-Length: {min(new_content_length, 1500)}".encode())

                if (packet_length + content_length_diff > 1500):
                    overflow = packet_length + content_length_diff - 1500
                    carry = data[-overflow:]
                    data = data[:-overflow]
                    addCarryToNextFrame = True

                packet[TCP][Raw].load = data
                print(packet[TCP][Raw].load)

                # Recompute checksum
                del packet[IP].chksum
                del packet[TCP].chksum

                print("========================================================================")
                print(packet.show())
                print(packet[TCP][Raw].load.decode(errors="ignore"))
                print("========================================================================")


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
