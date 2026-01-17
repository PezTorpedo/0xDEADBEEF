# 0xDEADBEEF

Repository for **Group 29 – Lab on Offensive Security Lab Project**.  
This project focuses on the security analysis and exploitation of the **Philips Hue ecosystem**.

---

## Repository Structure

### 📁 Attacks
Contains all implemented attacks against the target system, including scripts, data, and documentation.

- **Manual MITM Attack**  
  HTTP man-in-the-middle attack using NFTables, including the script and a screenshot of the result.

- **ZigBee Side-channel Attack**  
  Analysis and exploitation of ZigBee traffic, including raw and processed datasets, packet captures, testing utilities, and decoding scripts.
  
- **Physical Attack**  
  Attack performed with physical access to the device, including step-by-step documentation and a ARP spoofing script using scapy and a light signaling script that an attacker can use to achieve a man-in-the middle and control user lights.
---

### 📁 Packet Captures
Network traffic captures collected during the analysis phase, organized by interface and theme.

- **eth0**: Firmware updates, API interactions, token creation, and reconnaissance traffic.
- **zigbee**: ZigBee pairing and light control communication captures.

---

### 📁 Philips Hue Bridge
All artifacts extracted or analyzed from the Philips Hue Bridge.

- **Firmware**
  - Extracted flash memory (`mtd*.bin`)
  - Parsed filesystem directories
  - Boot logs, environment variables, and firmware metadata
  - Custom parsing script

- **Web Server**
  - Bridge API configuration files
  - Token-related data
  - License and package information

---

### 📁 Raspberry Pi
Configuration files related to the Raspberry Pi used as an attack platform, including network setup.
