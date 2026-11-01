#!/usr/bin/env python3
"""Read Razer Barracuda X Chroma battery via Linux hidraw; no dependencies."""
import functools
import json
import operator
import os
from pathlib import Path
import select
import time


def checksum(data):
    return functools.reduce(operator.xor, data, 0)


def request(prop):
    data = bytearray(64)
    data[:11] = bytes([2, 0, 96, 0, 0, 0, 4, 0, 0, 128, prop])
    data[62] = checksum(data[:62])
    return data


def parse_report(data):
    if (len(data) != 64 or data[0] != 2 or data[1] not in (2, 10)
            or data[2] != 96 or data[6:10] != bytes([5, 0, 128, 128])
            or data[11] != (2 if data[1] == 10 else 1) or data[12] != 1
            or checksum(data[1:62]) != data[62]):
        return None
    prop, value = data[10], data[13]
    if prop == 0x21 and value <= 100:
        return prop, value
    if prop in (0x20, 0x2a) and value <= 1:
        return prop, value
    return None


def read_battery():
    nodes = [p for p in Path('/sys/class/hidraw').glob('hidraw*')
             if 'HID_ID=0003:00001532:00000574' in (p / 'device/uevent').read_text()]
    if not nodes:
        return {'status': 'disconnected'}
    permission = False
    for node in nodes:
        try:
            fd = os.open('/dev/' + node.name, os.O_RDWR | os.O_NONBLOCK)
        except PermissionError:
            permission = True
            continue
        try:
            # Discard queued events before querying fresh state.
            for _ in range(256):
                if not select.select([fd], [], [], 0)[0]:
                    break
                os.read(fd, 64)
            values = {}
            for prop in (0x21, 0x2a):
                os.write(fd, request(prop))
                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline:
                    if not select.select([fd], [], [], max(0, deadline - time.monotonic()))[0]:
                        break
                    packet = parse_report(os.read(fd, 64))
                    if packet:
                        values[packet[0]] = packet[1]
                        if packet == (0x20, 0):
                            return {'status': 'disconnected'}
                        if packet[0] == prop:
                            break
            if 0x21 in values:
                return {'status': 'connected', 'percentage': values[0x21],
                        'charging': bool(values.get(0x2a, 0))}
        finally:
            os.close(fd)
    return {'status': 'permission' if permission else 'unavailable'}


class LiveState:
    def __init__(self):
        self.percentage = None
        self.charging = False
        self.status = 'waiting'

    def update(self, packet):
        prop, value = packet
        if prop == 0x20:
            self.percentage = None
            self.charging = False
            self.status = 'waiting' if value else 'disconnected'
        elif prop == 0x21:
            self.percentage = value
            self.status = 'connected'
        elif prop == 0x2a:
            self.charging = bool(value)
        if self.percentage is None:
            return {'status': self.status}
        return {'status': 'connected', 'percentage': self.percentage,
                'charging': self.charging}


def watch_device(fd):
    """Yield updates from one open HID handle; block between device events."""
    state = LiveState()

    def query():
        for prop in (0x21, 0x2a):
            os.write(fd, request(prop))
        return time.monotonic() + 3

    deadline = query()
    while True:
        timeout = max(0, deadline - time.monotonic()) if deadline else None
        if not select.select([fd], [], [], timeout)[0]:
            if state.percentage is None:
                # Reopen and retry if the headset did not answer at startup.
                raise TimeoutError('No battery response')
            deadline = None
            continue
        data = os.read(fd, 64)
        if not data:
            raise OSError('Dongle disconnected')
        packet = parse_report(data)
        if packet is None:
            continue
        snapshot = state.update(packet)
        if packet == (0x20, 1):
            deadline = query()
        elif packet == (0x20, 0):
            deadline = None
        yield snapshot


def watch():
    previous = None

    def emit(snapshot):
        nonlocal previous
        if snapshot != previous:
            print(json.dumps(snapshot), flush=True)
            previous = snapshot

    while True:
        fd = None
        try:
            nodes = []
            for node in Path('/sys/class/hidraw').glob('hidraw*'):
                try:
                    if 'HID_ID=0003:00001532:00000574' in (node / 'device/uevent').read_text():
                        nodes.append(node)
                except FileNotFoundError:
                    continue
            if not nodes:
                emit({'status': 'disconnected'})
            else:
                fd = os.open('/dev/' + nodes[0].name, os.O_RDWR | os.O_NONBLOCK)
                emit({'status': 'waiting'})
                for snapshot in watch_device(fd):
                    emit(snapshot)
        except PermissionError:
            emit({'status': 'permission'})
        except OSError:
            emit({'status': 'unavailable'})
        finally:
            if fd is not None:
                os.close(fd)
        # Only discovery/error recovery retries. Connected devices block on HID.
        time.sleep(3)


if __name__ == '__main__':
    import sys
    if '--watch' in sys.argv:
        watch()
    else:
        try:
            print(json.dumps(read_battery()))
        except OSError:
            print(json.dumps({'status': 'unavailable'}))
