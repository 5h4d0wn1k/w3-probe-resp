# W3 — WiFi Probe Responder

Probe request sniffing with optional auto-response and device tracking.

## Overview

This project implements a probe request sniffer that:
- Captures probe requests in promiscuous mode across all channels
- Extracts SSID names from directed probes
- Tracks unique devices with MAC, RSSI, channel, and probe count
- Optionally sends probe responses back to discovered devices
- Generates periodic device reports

## Hardware

| Component | Connection | Role |
|-----------|------------|------|
| ESP32-C6 Dev Board | Main board | Probe sniffing, optional response |

## Features

- **Probe Sniffing**: Captures all probe requests (directed and wildcard)
- **Device Tracking**: MAC address, SSID, RSSI, channel, probe count
- **Auto-Response**: Optional probe response transmission (disabled by default)
- **Channel Hopping**: Sweeps channels 1-13 for full coverage

## Configuration

Edit `AUTO_RESPOND` in the firmware to enable/disable probe responses:
```cpp
#define AUTO_RESPOND  false  // Set true to auto-respond to probes
```

## Serial Output

```
+----------------------------------------------+
|    W3 WiFi Probe Responder                   |
|    Board: ESP32-C6                           |
+----------------------------------------------+
Promiscuous mode active on channel 1
Auto-respond: DISABLED

[PROBE] src=AA:BB:CC:DD:EE:FF SSID="HomeWiFi" RSSI=-52 CH=6 total=1

+==============================================+
|     W3 Probe Responder - Device Report       |
+==============================================+
| Total Probes:    15                          |
| Tracked Devices: 3                           |
| Channel:         6                           |
+----------------------------------------------+
| Device MAC          | RSSI | CH | Probes     |
+----------------------------------------------+
| AA:BB:CC:DD:EE:FF |  -52 |  6 |     5  HomeWiFi |
```

## Build & Flash

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c6 firmware/
arduino-cli upload --fqbn esp32:esp32:esp32c6 --port /dev/ttyUSB0 firmware/
```

## Legal Disclaimer

**IMPORTANT: Read before use.**

This project is provided for **educational and authorized security testing purposes only**. 

### Authorization Requirements
- You MUST have explicit written permission from the network owner before using this tool
- Unauthorized interception of network communications is illegal under federal and state laws
- This tool should ONLY be used on networks you own or have written authorization to test

### Legal Framework
- **Computer Fraud and Abuse Act (CFAA)**: Unauthorized access to computer systems is a federal crime
- **Wiretap Act (18 U.S.C. § 2511)**: Interception of electronic communications without consent is illegal
- **State Laws**: Many states have additional computer crime and wiretapping statutes
- **GDPR/CCPA**: Data collection may be subject to privacy regulations

### Acceptable Use
- Testing security of your own networks
- Authorized penetration testing with written scope
- Academic research in controlled lab environments
- Security education and training

### Prohibited Use
- Intercepting communications on networks you don't own
- Attacking infrastructure without authorization
- Any activity that violates applicable laws or regulations
- Commercial use without proper licensing

### No Warranty
This software is provided "AS IS" without warranty of any kind. The author is not responsible for any misuse or damage caused by this software.

### Responsible Disclosure
If you discover vulnerabilities using this tool, follow responsible disclosure practices:
1. Report to the vendor/owner privately
2. Allow reasonable time for remediation
3. Do not exploit beyond proof of concept

## License

MIT
