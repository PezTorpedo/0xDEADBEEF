# 0xDEADBEEF

Repository for **Group 29 – Offensive Security Lab Project**.  
This project focuses on the security analysis and exploitation of the **Philips Hue ecosystem**, combining network, physical, and wireless attacks.

---

## Repository Structure

### 📁 Attacks
Contains all implemented attacks against the target system, including scripts, data, and documentation.

- **Manual MITM Attack**  
  HTTP man-in-the-middle attack using NFQUEUE, with proof-of-concept scripts and screenshots.

- **Physical Attack**  
  Attacks performed with physical access to the device, including ARP spoofing scripts, LED signaling, and step-by-step documentation.

- **ZigBee Side-channel Attack**  
  Analysis and exploitation of ZigBee traffic, including raw and processed datasets, packet captures, testing utilities, and decoding scripts.

---

### 📁 Packet Captures
Network traffic captures collected during the analysis phase, organized by interface and protocol.

- **eth0**: Firmware updates, API interactions, token creation, and reconnaissance traffic.
- **zigbee**: ZigBee pairing and light control communication captures.

---

### 📁 Philips Hue Bridge
All artifacts extracted or analyzed from the Philips Hue Bridge.

- **Firmware**
  - Extracted flash memory (`mtd*.bin`)
  - Parsed filesystem directories
  - Boot logs, environment variables, and firmware metadata
  - Custom parsing and analysis scripts

- **Web Server**
  - Bridge API configuration files
  - Token-related data
  - License and package information

---

### 📁 Raspberry Pi
Configuration files related to the Raspberry Pi used as an attack platform, including network setup and supporting infrastructure.
