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
- Responding to probes on real channels outside a licensed, authorized, shield-attenuated lab
- Any activity that violates applicable laws or regulations — the Python engine reproduces the
  ESP32 firmware logic as bytes only and transmits nothing
- Commercial use without proper licensing

### Regulatory Framework
- **Federal Communications Act (47 U.S.C. § 333)**: Willful interference with authorized radio communications is prohibited.
- **47 CFR Part 15**: Unauthorized intentional radiators are regulated; this repo is byte-level only and emits nothing.
- **CFAA (18 U.S.C. § 1030) / ECPA**: Impersonating access points on networks you don't own is a federal crime.

## Live Lab Test Plan

Offline (this repo, no radio):
1. `python3 firmware/probe_resp.py` — 3 clients probe lab SSIDs; responsive-vs-silent
   fingerprint per client, exit 0.
2. `python3 firmware/probe_resp.py --gen-fixture reports/exchange.pcap --pcap reports/exchange.pcap
   --json reports/w3.json` — exchange round-trip + fingerprint (exit 0).
3. `python3 firmware/probe_resp.py --wildcard --json reports/w3w.json` — wildcard-probe window
   comparison (exit 0).
4. `python3 -m unittest discover -s tests` — byte-exact DA=client-SA, silent-SSID tests (exit 0).

Authorized lab:
5. On your own lab AP, probe `lab-internal` (responsive) and a quiet/non-broadcast SSID
   (should be silent) and compare the fingerprint against the simulator.
6. `green = permitted`: simulating probe responses as bytes, or (with written scope + shield)
   testing your own ESP32 responder in a lab enclosure.

## Metrics

- Probe-request parse (byte-exact): SA, probe SSID incl. `<hidden>` wildcard sentinel
- Probe-response build (byte-exact): DA = requesting client SA (unicast), SA/BSSID = lab AP,
  SSID IE answered for allowlisted SSIDs only, rates IE 0x82/0x84/0x0B/0x16
- responsive-vs-silent policy: allowed set vs silent/unknown set; wildcard gated by flag
- Client fingerprint: probed SSID list, answering-AP SSIDs, responsive_count, verdict
- pcap classic (linktype 105) exchange fixture + fingerprint; captures/ and reports/ gitignored
- Offline: all frames synthesized as bytes via frame_core; no radio, no wall-clock data

- Test suite: `python3 -m unittest discover -s tests`
- Reports: `reports/` (gitignored)

## License

MIT
