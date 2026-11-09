#!/usr/bin/env python3
"""Razer Barracuda X Chroma (USB dongle 1532:0574) over hidraw.

  barracuda.py status        -> {"present", "connected", "battery", "charging"} as JSON
  barracuda.py color RRGGBB  -> every earcup lamp to one static colour (000000 = dark)

Battery and link come from the headset's vendor protocol (report 0x02: a GET written as an output report, the answer read back
as a feature report). Lighting is the standard HID LampArray on the same interface: autonomous mode off, then one range update.
Needs read/write on the hidraw node; 70-razer-barracuda.rules grants it to the seat user.
"""
import fcntl
import glob
import json
import os
import re
import sys
import time

HID_ID = "0003:00001532:00000574"
PROP_LINK, PROP_BATTERY, PROP_CHARGING, PROP_LIGHTS = 0x20, 0x21, 0x2A, 0x40
LIGHTS_ON = 0x0C
LAMP_ATTRIBUTES, LAMP_RANGE_UPDATE, LAMP_CONTROL = 0x31, 0x35, 0x36


def _ioctl(nr: int, size: int) -> int:
    return (3 << 30) | (size << 16) | (ord("H") << 8) | nr


def find_node() -> str | None:
    for uevent in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        try:
            with open(uevent) as f:
                if f"HID_ID={HID_ID}" in f.read().split():
                    return "/dev/" + uevent.split("/")[-3]
        except OSError:
            continue
    return None


def vendor_report(prop: int, data: bytes = b"", write: bool = False) -> bytes:
    buf = bytearray(64)
    buf[0], buf[2], buf[6], buf[9] = 0x02, 0x60, len(data) + 4, 0x80
    buf[10] = prop | (0x80 if write else 0)
    buf[12] = len(data)
    buf[13 : 13 + len(data)] = data
    checksum = 0
    for b in buf[:62]:
        checksum ^= b
    buf[62] = checksum
    return bytes(buf)


def get_feature(fd: int, report_id: int, size: int) -> bytes:
    buf = bytearray(size)
    buf[0] = report_id
    fcntl.ioctl(fd, _ioctl(0x07, size), buf)
    return bytes(buf)


def set_feature(fd: int, data: bytes) -> None:
    fcntl.ioctl(fd, _ioctl(0x06, len(data)), bytearray(data))


def query(fd: int, prop: int) -> int | None:
    """One vendor GET. The dongle answers into feature report 0x02; a stale or foreign answer is retried, never trusted."""
    for _ in range(3):
        os.write(fd, vendor_report(prop))
        time.sleep(0.1)
        reply = get_feature(fd, 0x02, 64)
        if reply[2] == 0x60 and reply[10] == prop:
            return reply[13]
    return None


def status(fd: int) -> dict:
    connected = query(fd, PROP_LINK) == 1
    battery = query(fd, PROP_BATTERY) if connected else None
    charging = query(fd, PROP_CHARGING) if connected else None
    return {
        "present": True,
        "connected": connected,
        "battery": battery if battery is not None and 0 <= battery <= 100 else None,
        "charging": charging == 1,
    }


def set_color(fd: int, rgb: str) -> None:
    r, g, b = (int(rgb[i : i + 2], 16) for i in (0, 2, 4))
    lamp_count = int.from_bytes(get_feature(fd, LAMP_ATTRIBUTES, 23)[1:3], "little")
    if not 1 <= lamp_count <= 64:
        raise OSError(f"unexpected LampArray lamp count {lamp_count}")
    os.write(fd, vendor_report(PROP_LIGHTS, bytes([LIGHTS_ON]), write=True))
    set_feature(fd, bytes([LAMP_CONTROL, 0]))  # host drives the lamps, not the firmware effect
    last = lamp_count - 1
    set_feature(fd, bytes([LAMP_RANGE_UPDATE, 0x01, 0, 0, last & 0xFF, last >> 8, r, g, b, 0xFF]))


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "color" and re.fullmatch(r"[0-9A-Fa-f]{6}", argv[2]):
        command = "color"
    elif argv[1:] == ["status"]:
        command = "status"
    else:
        print("usage: barracuda.py status | color RRGGBB", file=sys.stderr)
        return 2

    node = find_node()
    if node is None:
        if command == "status":
            print(json.dumps({"present": False, "connected": False, "battery": None, "charging": False}))
            return 0
        print("Barracuda dongle not found", file=sys.stderr)
        return 1

    try:
        fd = os.open(node, os.O_RDWR)
    except PermissionError:
        print(f"No access to {node}: install 70-razer-barracuda.rules", file=sys.stderr)
        return 1
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)  # a status poll and a colour change must not interleave their request/reply pairs
        if command == "status":
            print(json.dumps(status(fd)))
        else:
            set_color(fd, argv[2])
        return 0
    except OSError as e:
        print(f"Barracuda I/O failed: {e}", file=sys.stderr)
        return 1
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
