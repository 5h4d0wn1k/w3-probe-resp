> **⚠️ EDUCATIONAL USE ONLY — AUTHORIZED TESTING ONLY.**
> This project exists for education, research, and **defense of systems you own
> or hold explicit written authorization to assess**. Unauthorized use is
> prohibited and may be illegal. Read [ETHICS.md](ETHICS.md) and
> [SCOPE.md](SCOPE.md) before use. Use at your own risk; **AS IS**, no warranty.

# W3 — WiFi Probe Responder (Probe-Request Sniffer & Response Simulator)

[![License](https://img.shields.io/github/license/5h4d0wn1k/w3-probe-resp)](LICENSE)
[![Stars](https://img.shields.io/github/stars/5h4d0wn1k/w3-probe-resp)](https://github.com/5h4d0wn1k/w3-probe-resp/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/5h4d0wn1k/w3-probe-resp)](https://github.com/5h4d0wn1k/w3-probe-resp/commits/master)
[![Issues](https://img.shields.io/github/issues/5h4d0wn1k/w3-probe-resp)](https://github.com/5h4d0wn1k/w3-probe-resp/issues)

**W3** is a Wi-Fi probe-request analysis project for wireless security
experiments: an ESP32-C6 firmware sniffer that captures probe requests in
promiscuous mode, tracks devices, and optionally auto-responds — paired with a
byte-exact, offscreen Python simulation engine for probe-response fingerprinting.

## Why W3?

Probe requests reveal the SSID lists devices actively hunt for, making them a
core topic in wireless security education. W3 gives learners a hands-on path:
flash an ESP32-C6 with the Arduino sketch to observe real probe traffic
(MAC, SSID, RSSI, channel, probe count) across channels 1–13, then use the
pure-Python simulator to understand how an access point would answer each
client — with fully deterministic, radio-free frame exchange. The offscreen
default keeps everything ethical and lab-safe.

## Features

- **Promiscuous probe sniffing** — ESP32-C6 firmware captures directed and
  wildcard probe requests (`firmware/w3_probe_resp/w3_probe_resp.ino`).
- **Device tracking** — MAC, SSID, RSSI, channel, and per-device probe counts
  surfaced over serial.
- **Optional auto-response** — `AUTO_RESPOND` toggle (disabled by default) to
  send probe responses via `esp_wifi_80211_tx`.
- **Channel hopping** — Sweeps channels 1–13 for full coverage.
- **Offscreen simulation engine** — `firmware/probe_resp.py` parses probe
  requests, builds byte-exact probe-response frames, and fingerprints clients
  with `--pcap` and `--gen-fixture` modes.
- **FCS verification** — frame check sequences verified via
  `firmware/frame_core.py`.
- **Unit tests** — `tests/test_probe_resp.py` covers allowed, silent, and
  unknown-SSID responder behavior.

## Quickstart

### Prerequisites

- ESP32-C6 board, Arduino CLI with `esp32:esp32:esp32c6` core
- Python 3.8+ for the simulator

### Flash the ESP32-C6 firmware

```bash
arduino-cli compile --fqbn esp32:esp32:esp32c6 firmware/w3_probe_resp/
arduino-cli upload --fqbn esp32:esp32:esp32c6 --port /dev/ttyUSB0 firmware/w3_probe_resp/
```

To enable probe auto-response, set `#define AUTO_RESPOND true` in
`firmware/w3_probe_resp/w3_probe_resp.ino`.

### Run the offscreen simulation

```bash
python3 firmware/probe_resp.py
python3 firmware/probe_resp.py --wildcard
python3 firmware/probe_resp.py --gen-fixture exchange.pcap
python3 firmware/probe_resp.py --pcap exchange.pcap --json report.json
```

### Tests

```bash
python3 -m pytest tests/
```

## Project Structure

- `firmware/w3_probe_resp/w3_probe_resp.ino` — ESP32-C6 Arduino sketch
  (sniffer, tracker, auto-responder).
- `firmware/probe_resp.py` — Python probe-response simulation + fingerprinting
  CLI.
- `firmware/frame_core.py` — 802.11 frame build/parse and FCS helpers.
- `tests/` — Responder behavior unit tests.

## Documentation

- [ETHICS.md](ETHICS.md) — Educational purpose and authorized use only.
- [SCOPE.md](SCOPE.md) — Authorized scope of research.
- [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md),
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Contributing

Contributions for educational and authorized wireless-testing research are
welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT License — see [LICENSE](LICENSE) for details.

> **⚠️ EDUCATIONAL USE ONLY — AUTHORIZED TESTING ONLY.**