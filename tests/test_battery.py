import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugin'))
import battery


def reply(prop, value, event=False):
    data = bytearray(64)
    data[:14] = bytes([2, 10 if event else 2, 96, 0, 0, 0, 5, 0, 128, 128, prop, 2 if event else 1, 1, value])
    data[62] = battery.checksum(data[1:62])
    return bytes(data)


class ProtocolTest(unittest.TestCase):
    def test_get_packet(self):
        data = battery.request(0x21)
        self.assertEqual(len(data), 64)
        self.assertEqual(data[:11], bytes.fromhex('02 00 60 00 00 00 04 00 00 80 21'))
        self.assertEqual(data[62], battery.checksum(data[:62]))

    def test_valid_reports(self):
        self.assertEqual(battery.parse_report(reply(0x21, 73)), (0x21, 73))
        self.assertEqual(battery.parse_report(reply(0x2a, 1, True)), (0x2a, 1))
        self.assertEqual(battery.parse_report(reply(0x21, 0)), (0x21, 0))

    def test_rejects_invalid_reports(self):
        for data in [b'', bytes(64), reply(0x21, 101), reply(0x2a, 2), reply(0x13, 7)]:
            self.assertIsNone(battery.parse_report(data))
        data = bytearray(reply(0x21, 73))
        data[13] = 50
        self.assertIsNone(battery.parse_report(data))


class LiveStateTest(unittest.TestCase):
    def test_events_update_without_queries_and_clear_on_disconnect(self):
        state = battery.LiveState()
        self.assertEqual(state.update((0x21, 59)),
                         {'status': 'connected', 'percentage': 59, 'charging': False})
        self.assertEqual(state.update((0x2a, 1))['charging'], True)
        self.assertEqual(state.update((0x21, 60))['percentage'], 60)
        self.assertEqual(state.update((0x20, 0)), {'status': 'disconnected'})
        self.assertEqual(state.update((0x20, 1)), {'status': 'waiting'})
        self.assertEqual(state.update((0x21, 42)),
                         {'status': 'connected', 'percentage': 42, 'charging': False})

    def test_stream_emits_live_changes_and_detects_unplug(self):
        import socket
        host, headset = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        try:
            stream = battery.watch_device(host.fileno())
            headset.send(reply(0x21, 59))
            self.assertEqual(next(stream)['percentage'], 59)
            self.assertEqual(headset.recv(64), battery.request(0x21))
            self.assertEqual(headset.recv(64), battery.request(0x2a))
            headset.send(reply(0x2a, 1, True))
            self.assertTrue(next(stream)['charging'])
            headset.send(reply(0x21, 60, True))
            self.assertEqual(next(stream)['percentage'], 60)
            # Ordinary battery/charging events must not trigger new queries.
            headset.setblocking(False)
            with self.assertRaises(BlockingIOError):
                headset.recv(64)
            headset.send(reply(0x20, 0, True))
            self.assertEqual(next(stream), {'status': 'disconnected'})
            headset.send(reply(0x20, 1, True))
            self.assertEqual(next(stream), {'status': 'waiting'})
            self.assertEqual(headset.recv(64), battery.request(0x21))
            self.assertEqual(headset.recv(64), battery.request(0x2a))
            headset.close()
            with self.assertRaises(OSError):
                next(stream)
        finally:
            host.close()
            headset.close()


if __name__ == '__main__':
    unittest.main()
