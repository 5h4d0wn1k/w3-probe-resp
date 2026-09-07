#!/usr/bin/env python3
"""Byte-exact unit tests for w3-probe-resp."""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from firmware import probe_resp as pr
from firmware import frame_core as fc


def make_req(ssid="lab-internal", sa="00:11:22:44:00:09"):
    req = fc.build_probe_request(ssid=ssid, sa=sa, bssid="ff:ff:ff:ff:ff:ff", seq_num=1)
    p, _ = fc.parse_probe_request(req)
    return p


class ResponderTest(unittest.TestCase):
    def test_responds_to_allowed(self):
        r = pr.ProbeResponder()
        resp = r.respond(make_req("lab-internal"))
        self.assertIsNotNone(resp)
        self.assertTrue(fc.verify_fcs(resp))
        parsed, _ = fc.parse_probe_response(resp[:-4])
        self.assertEqual(parsed["ssid"], "lab-internal")

    def test_silent_for_silent_ssid(self):
        r = pr.ProbeResponder()
        self.assertIsNone(r.respond(make_req(pr.SILENT_SSID)))

    def test_is_silent_for_unknown(self):
        r = pr.ProbeResponder()
        self.assertIsNone(r.respond(make_req("lab-other")))

    def test_wildcard_gated(self):
        r = pr.ProbeResponder(wildcard=False)
        self.assertIsNone(r.respond(make_req("")))
        r2 = pr.ProbeResponder(wildcard=True)
        self.assertIsNotNone(r2.respond(make_req("")))

    def test_response_da_equals_client_sa(self):
        r = pr.ProbeResponder()
        p = make_req("lab-internal", sa="00:11:22:44:00:09")
        resp = r.respond(p)
        fields, _ = fc.parse_mgmt_header(resp[:-4])
        self.assertEqual(fields["da"], "00:11:22:44:00:09")


class FingerprintTest(unittest.TestCase):
    def test_responsive_vs_silent(self):
        clients = [
            {"sa": "00:11:22:44:00:01", "ssids": ["lab-internal", "lab-guest-open"]},
            {"sa": "00:11:22:44:00:02", "ssids": ["lab-internal", pr.SILENT_SSID]},
        ]
        frames = pr.build_exchange(clients, pr.ProbeResponder())
        fp = pr.fingerprint_from_frames(frames, pr.ProbeResponder())
        self.assertEqual(fp["clients"]["00:11:22:44:00:01"]["responsive_count"], 2)
        self.assertIn(pr.SILENT_SSID, fp["clients"]["00:11:22:44:00:02"]["probed"])
        self.assertNotIn(pr.SILENT_SSID, fp["clients"]["00:11:22:44:00:02"]["answering_ssids"])


class FixtureTest(unittest.TestCase):
    def test_pcap_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "exchange.pcap")
            clients = [{"sa": "00:11:22:44:00:01", "ssids": ["lab-internal"]}]
            n = pr.write_exchange_fixture(path, clients, pr.ProbeResponder())
            self.assertGreater(n, 1)
            fp = pr.fingerprint_pcap(path)
            self.assertEqual(fp["clients"]["00:11:22:44:00:01"]["responsive_count"], 1)


class CLITest(unittest.TestCase):
    def test_demo_exit_zero(self):
        self.assertEqual(pr.run_demo(), 0)

    def test_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "o.json")
            rc = pr.main(["--json", out])
            self.assertEqual(rc, 0)
            data = json.load(open(out))
            self.assertFalse(data["radio_emitted"])
            self.assertEqual(len(data["clients"]), 3)


if __name__ == "__main__":
    unittest.main()