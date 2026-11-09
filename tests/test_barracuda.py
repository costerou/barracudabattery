import importlib.util
import json
import pathlib
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("barracuda", pathlib.Path(__file__).parents[1] / "barracuda.py")
barracuda = importlib.util.module_from_spec(spec)
spec.loader.exec_module(barracuda)


class VendorReport(unittest.TestCase):
    def test_get_battery_matches_captured_frame(self):
        frame = barracuda.vendor_report(0x21)
        self.assertEqual(len(frame), 64)
        self.assertEqual(frame[:13].hex(), "02006000000004000080210000")
        self.assertEqual(frame[62], 0x02 ^ 0x60 ^ 0x04 ^ 0x80 ^ 0x21)

    def test_set_sets_write_flag_and_payload(self):
        frame = barracuda.vendor_report(0x40, bytes([0x0C]), write=True)
        self.assertEqual((frame[6], frame[10], frame[12], frame[13]), (5, 0xC0, 1, 0x0C))


class Cli(unittest.TestCase):
    def test_rejects_non_hex_colour_before_touching_device(self):
        with mock.patch.object(barracuda, "find_node") as find:
            for bad in (["x", "color", "zz"], ["x", "color", "ff00ff;rm"], ["x", "color", "#ff00ff"], ["x"]):
                self.assertEqual(barracuda.main(bad), 2)
            find.assert_not_called()

    def test_status_without_dongle_is_not_an_error(self):
        with mock.patch.object(barracuda, "find_node", return_value=None), mock.patch("builtins.print") as out:
            self.assertEqual(barracuda.main(["x", "status"]), 0)
        self.assertEqual(json.loads(out.call_args[0][0])["present"], False)

    def test_stale_reply_is_not_trusted(self):
        stale = bytearray(64)
        stale[2], stale[10], stale[13] = 0x60, 0x20, 1  # answer to a different property
        with mock.patch.object(barracuda.os, "write"), mock.patch.object(barracuda.time, "sleep"), \
                mock.patch.object(barracuda, "get_feature", return_value=bytes(stale)):
            self.assertIsNone(barracuda.query(0, 0x21))


if __name__ == "__main__":
    unittest.main()
