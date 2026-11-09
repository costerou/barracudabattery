# Barracuda

Omarchy bar widget for the **Razer Barracuda X Chroma** (2.4 GHz USB dongle, `1532:0574`): battery level in the bar
(`72%`, `+` while charging), and a panel to pick the earcup light colour.

- Battery is read every 60 seconds; right-click the icon to read it now.
- Click the icon for 10 colour swatches (including Off) or type any hex colour. The choice is saved in `shell.json`
  and re-applied whenever the headset reconnects.
- Python 3 standard library only. No OpenRazer, HeadsetControl, or Synapse.

## Install

```sh
omarchy plugin add https://github.com/costerou/barracudabattery --enable
```

Then allow your desktop session to access the headset (one time):

```sh
sudo install -m 644 ~/.config/omarchy/plugins/cody.barracuda/70-razer-barracuda.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --action=change --subsystem-match=hidraw
```

The rule only matches this headset's dongle. Remove the file to undo.

## How it talks to the headset

`barracuda.py status` prints `{"present", "connected", "battery", "charging"}` as JSON, using the headset's vendor
report `0x02` (properties `0x20` link, `0x21` battery, `0x2A` charging). `barracuda.py color RRGGBB` sets all lamps
through the standard HID LampArray reports (`0x36` autonomous mode off, `0x35` range update). The vendor protocol is
reverse-engineered, so firmware updates may change it.

## Tests

```sh
python3 -m unittest discover -s tests
```
