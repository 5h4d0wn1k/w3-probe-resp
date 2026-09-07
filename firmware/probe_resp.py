#!/usr/bin/env python3
"""W3 — Probe Responder (offscreen AP response simulation).

Simulates the ESP32-C6 probe-responder logic from the firmware sketch as
byte-exact frames, then runs a client fingerprint pass:

  * AP identity: lab BSSID (00:11:22 OUI) hosting `lab-*` SSIDs
  * responsive vs silent: the AP answers probe requests for SSIDs on its
    allowlist (or wildcard if enabled) and stays silent for `--silent` SSIDs
  * probe-request parse -> build probe-response with DA = client SA
  * pcap exchange fixture + per-client response fingerprints

Pure-stdlib bytes; passive simulation; this engine never transmits radio.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import defaultdict

try:
    from firmware import frame_core as fc
except ImportError:
    try:
        import frame_core as fc
    except ImportError:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "firmware"))
        import frame_core as fc

START_TS = 1700000000.0
AP_BSSID = "00:11:22:33:44:55"
SILENT_SSID = "lab-secret-norx"


# ----------------------------------------------------------------------
# Probe-response decision logic (mirrors the .ino AUTO_RESPOND path)
# ----------------------------------------------------------------------

def _answered_ssid(req: dict, responder: 'ProbeResponder') -> str:
    known = req.get("ssid", "")
    if known in ("", "<hidden>"):
        return responder.ssid      # wildcard probe -> own SSID
    return known


def build_response_to(req: dict, responder: 'ProbeResponder', seq_num: int = 0) -> bytes:
    """Probe response with DA = requesting client SA (unicast, as on the wire)."""
    client = fc.mac_bytes(req["sa"])
    hdr = fc.build_mgmt_header(fc.FC_SUBTYPE_PROBE_RESP, client, fc.mac_bytes(responder.bssid),
                               fc.mac_bytes(responder.bssid), seq_num=seq_num)
    body = struct.pack("<QH", 3000, 100)
    body += struct.pack("<H", 0x0431)
    body += fc.build_ssid_ie(_answered_ssid(req, responder))
    body += fc.build_rates_ie([0x82, 0x84, 0x0b, 0x16])
    return hdr + body


class ProbeResponder:
    """An AP that answers probes for allowed SSIDs and ignores silent ones."""

    def __init__(self, bssid: str = AP_BSSID, ssid: str = "lab-internal",
                 allowed: tuple = ("lab-internal", "lab-guest-open"),
                 silent: tuple = (SILENT_SSID,), wildcard: bool = False):
        self.bssid = bssid
        self.ssid = ssid
        self.allowed = set(allowed)
        self.silent = set(silent)
        self.wildcard = wildcard
        self.responses_sent = 0
        self.probes_seen = 0

    def decide(self, req_ssid: str) -> bool:
        """Responsive(True) / silent(False) for a probed SSID."""
        self.probes_seen += 1
        req_ssid = "" if req_ssid == "<hidden>" else req_ssid
        if req_ssid == "":
            return self.wildcard
        if req_ssid in self.allowed:
            return True
        return False

    def respond(self, req: dict, seq_num: int = 0) -> bytes | None:
        """Return a probe-response frame for the prober, or None (silent)."""
        if not self.decide(req.get("ssid", "")):
            return None
        self.responses_sent += 1
        resp = build_response_to(req, self, seq_num=seq_num)
        return resp + fc.fcs(resp)


# ----------------------------------------------------------------------
# Exchange traffic builder + pcap fixtures
# ----------------------------------------------------------------------

def build_exchange(clients: list[dict], responder: ProbeResponder,
                   base: float = START_TS) -> list[dict]:
    """clients: [{sa, ssids: [...] }]; returns probe reqs + AP responses."""
    frames = []
    seq = 0
    for ci, client in enumerate(clients):
        for ssid in client["ssids"]:
            seq = (seq + 1) & 0xFFFF
            req = fc.build_probe_request(ssid=ssid, sa=client["sa"],
                                         bssid="ff:ff:ff:ff:ff:ff", seq_num=seq)
            p, _ = fc.parse_probe_request(req)
            frames.append({"ts": base + 0.02 * len(frames), "kind": "probe-request",
                           "sa": client["sa"], "ssid": p["ssid"], "data": req + fc.fcs(req)})
            resp = responder.respond(p, seq_num=(seq + 1) & 0xFFFF)
            if resp:
                frames.append({"ts": base + 0.02 * len(frames) + 0.005,
                               "kind": "probe-response", "sa": responder.bssid,
                               "ssid": ssid, "data": resp})
            seq += 1
    return frames


def write_exchange_fixture(path: str, clients: list[dict], responder: ProbeResponder) -> int:
    frames = build_exchange(clients, responder)
    fc.write_pcap(path, [f["data"] for f in frames], ts=frames[0]["ts"])
    return len(frames)


# ----------------------------------------------------------------------
# Client fingerprint (from a pcap: which SSIDs were answered?)
# ----------------------------------------------------------------------

def fingerprint_pcap(path: str) -> dict:
    probes = defaultdict(list)
    responses = defaultdict(list)
    for rec in fc.read_pcap(path):
        data = rec["data"]
        if not fc.verify_fcs(data):
            continue
        payload = data[:-4]
        try:
            fields, _ = fc.parse_mgmt_header(payload)
            if fields["subtype_val"] == fc.FC_SUBTYPE_PROBE_REQ:
                p, _ = fc.parse_probe_request(payload)
                probes[fields["sa"]].append(p["ssid"])
            elif fields["subtype_val"] == fc.FC_SUBTYPE_PROBE_RESP:
                p, _ = fc.parse_probe_response(payload)
                responses[p["ssid"]].append(fields["sa"])
        except ValueError:
            continue
    clients = {}
    for sa, ssids in probes.items():
        answered = {s for s in ssids if any(s == r for r in responses)}
        clients[sa] = {"probed": sorted(set(ssids)),
                       "answering_ssids": sorted(answered),
                       "responsive_count": len(answered),
                       "verdict": "responsive" if answered else "silent"}
    return {"clients": clients}


# ----------------------------------------------------------------------
# CLI / demo
# ----------------------------------------------------------------------

def build_args_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="w3-probe-resp",
        description="Probe responder simulator: byte-exact probe-request/response exchange, "
                    "responsive-vs-silent SSID policy, client response fingerprinting. "
                    "Pure-stdlib bytes; offline; no radio.")
    p.add_argument("--pcap", metavar="PATH", help="fingerprint a probe-exchange pcap")
    p.add_argument("--gen-fixture", metavar="PATH", help="write probe-exchange fixture")
    p.add_argument("--wildcard", action="store_true", help="respond to wildcard probes")
    p.add_argument("--json", metavar="PATH", help="write JSON report")
    return p


def print_fingerprint(fp: dict) -> None:
    print("=" * 62)
    print(" W3 — Probe Responder (offscreen exchange + fingerprint)")
    print("=" * 62)
    for sa, c in fp["clients"].items():
        probed = ",".join(c["probed"]) or "<wildcard>"
        answered = ",".join(c["answering_ssids"]) or "<none>"
        print(f"\n[+] client {sa}  probed=[{probed}]  answered=[{answered}]")
        print(f"    verdict: {c['verdict']}  (responses: {c['responsive_count']})")
    print("\n[+] exchange simulated as bytes — no radio emitted.")
    print("=" * 62)


def main(argv=None) -> int:
    args = build_args_parser().parse_args(argv)
    responder = ProbeResponder(wildcard=args.wildcard)
    clients = [
        {"sa": "00:11:22:44:00:01", "ssids": ["lab-internal", "lab-guest-open"]},
        {"sa": "00:11:22:44:00:02", "ssids": ["lab-internal", "lab-secret-norx"]},
        {"sa": "00:11:22:44:00:03", "ssids": ["", "lab-internal"]},
    ]
    if args.gen_fixture or not args.pcap:
        frames = build_exchange(clients, responder)
        print("[+] probe requests -> probe responses simulated as bytes")
    if args.gen_fixture:
        d = os.path.dirname(args.gen_fixture)
        if d:
            os.makedirs(d, exist_ok=True)
        n = write_exchange_fixture(args.gen_fixture, clients, ProbeResponder(wildcard=args.wildcard))
        print(f"\n[+] fixture -> {args.gen_fixture} ({n} frames)")
    fp = fingerprint_from_frames(frames, responder) if not args.pcap else fingerprint_pcap(args.pcap)
    print_fingerprint(fp)
    if args.json:
        d = os.path.dirname(args.json)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({"name": "w3-probe-resp", "radio_emitted": False, **fp},
                      f, indent=2, default=str)
    return 0


def fingerprint_from_frames(frames: list[dict], responder: ProbeResponder) -> dict:
    probes = defaultdict(list)
    responses = set()
    for f in frames:
        if f["kind"] == "probe-request":
            probes[f["sa"]].append(f["ssid"])
        elif f["kind"] == "probe-response":
            responses.add(f["ssid"])
    clients = {}
    for sa, ssids in probes.items():
        answered = {s for s in ssids if s in responses}
        clients[sa] = {"probed": sorted(set(ssids)),
                       "answering_ssids": sorted(answered),
                       "responsive_count": len(answered),
                       "verdict": "responsive" if answered else "silent"}
    return {"clients": clients}


def run_demo() -> int:
    return main([])


if __name__ == "__main__":
    raise SystemExit(main())