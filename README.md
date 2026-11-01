<img src="assets/icon.svg" width="64" height="64" alt="Barracuda Battery icon">

# Barracuda Battery

Live battery percentage for the **Razer Barracuda X Chroma** in your Omarchy
bar. A headphone icon and percentage sit alongside your tray icons, with a
charging marker while the headset is charging.

Battery and charging changes update as soon as the headset reports them.
There is no refresh button or periodic battery polling.

## Features

- Always-visible battery percentage beside a headphone icon.
- Charging indicator and your theme's urgent color at 20% or below.
- One shared listener for all monitors, sleeping between headset events.
- Automatic recovery after disconnecting the headset or USB dongle.
- Theme-matched colors and fonts, with status details on hover.
- Local operation: no accounts, network requests, or telemetry.

## Compatibility and dependencies

- **Omarchy with the Quickshell bar** and the `omarchy plugin` commands.
  This is not a Waybar module.
- **Razer Barracuda X Chroma**, connected through its **2.4 GHz USB dongle**
  (USB vendor/product ID `1532:0574`). Other Barracuda models and direct
  Bluetooth connections are not supported.
- **Python 3**, using only its standard library. No pip packages, OpenRazer,
  HeadsetControl, or Razer Synapse are required.
- **Git** for installation through Omarchy, and **systemd/udev** plus **sudo**
  for the one-time device-access setup below.
- Omarchy's icon font for the headphone glyph.

The widget is designed for a horizontal bar, with the default placement in
its right section. It has been tested on the author's Omarchy system with
this headset and two monitors; no minimum Omarchy version has been established.
English status strings are included, with Omarchy's translation fallback.

## Install

### 1. Add the plugin

Run as your normal desktop user:

```sh
omarchy plugin add https://github.com/costerou/barracudabattery --enable
```

Omarchy installs the plugin and enables it in the bar's right section. Use
Omarchy's bar layout controls to position it beside your tray icons.

### 2. Allow access to the headset

**Manual setup is required.** Installing or enabling the plugin does not run
privileged setup automatically. Download a source checkout to review and
install the included device-access rule:

```sh
git clone https://github.com/costerou/barracudabattery.git barracuda-battery-setup
cd barracuda-battery-setup
cat 70-barracuda-battery.rules
sudo install -m 644 70-barracuda-battery.rules /etc/udev/rules.d/70-barracuda-battery.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --action=add --subsystem-match=hidraw
udevadm settle
```

The rule grants the active local desktop session access to this model's HID
interface. It does not grant access to every HID device or run the widget as
root. The listener retries automatically after setup; reconnect the dongle
if device access is still unavailable.

### Alternative: install from a checkout

For local development or to place the widget immediately after the tray:

```sh
git clone https://github.com/costerou/barracudabattery.git
cd barracudabattery
python3 install.py
```

Choose one installation method. The checkout installer installs the same
udev rule, copies the plugin into your Omarchy configuration, and adds it to
`shell.json` immediately after `omarchy.tray`. Running this command explicitly
applies those configuration changes. It preserves other widgets and saves a
timestamped backup before changing the layout. Re-running it updates the
plugin without adding a duplicate widget.

Changes normally hot-reload. If the widget does not appear, run:

```sh
omarchy restart shell
```

## Usage

The widget updates automatically. Hover to see the headset name and status.

- **Percentage:** the most recent whole percentage reported by the headset.
- **ϟ:** the headset reports that it is actively charging.
- **Urgent color:** battery is at or below 20%.
- **—:** waiting for a reading, disconnected, or unable to access the device.
  Hover for details.

A fully charged headset can report that it is no longer charging even while
its charging cable remains connected. Switching to Bluetooth can make the
headset unavailable through the USB dongle.

## How it works and permissions

A shared Python helper opens the matching Linux `hidraw` interface. It sends
battery and charging GET requests on startup and wireless reconnection, then
waits for pushed HID events. It does not change audio, lighting, EQ, or other
headset settings. Discovery and error recovery retry every three seconds.
A disconnect clears the displayed percentage instead of retaining an old value.

The QML widget reads the helper's JSON output. Reports are checked for framing,
checksum, property, and value range. No separate system service is installed;
the helper runs as a child of Quickshell under your desktop user.

Like other Omarchy shell plugins, this code runs unsandboxed. The only
privileged installation step is adding and applying the device-access rule.
The optional checkout installer also modifies your user bar layout as described
above. Neither installation method edits packaged files in `/usr/share/omarchy`.

## Update

For an Omarchy-managed installation:

```sh
omarchy plugin update cody.barracuda-battery
```

For a checkout installation, run `git pull --ff-only` in the checkout and then
`python3 install.py`. If an update changes the udev rule, review and apply the
updated rule using the setup steps above.

## Remove

```sh
omarchy plugin remove cody.barracuda-battery
```

To also remove the device-access rule installed for this plugin:

```sh
sudo rm -f /etc/udev/rules.d/70-barracuda-battery.rules
sudo udevadm control --reload-rules
```

Reconnect the dongle to apply the removal. Keep the rule if you still use it
for another application that accesses this headset. Timestamped `shell.json`
backups from the checkout installer are retained for you to manage.

## Troubleshooting and development

Check that `lsusb` shows `1532:0574`, the headset is on, and the 2.4 GHz link
is active. A permission status usually means the udev setup has not applied.
An unavailable status means a valid battery response has not arrived.

From a source checkout, request a single diagnostic reading:

```sh
python3 plugin/battery.py
```

Example output:

```json
{"status": "connected", "percentage": 59, "charging": true}
```

For live diagnostics, run `python3 plugin/battery.py --watch` and stop it with
Ctrl+C. Avoid running a second live listener alongside the installed widget:
concurrent HID readers may interfere with event delivery on this device.

Validate the distribution manifest and run the protocol/event tests:

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests
```

Report problems through [GitHub Issues](https://github.com/costerou/barracudabattery/issues),
including your Omarchy version, USB ID, and diagnostic status.

## License and acknowledgments

[MIT License](LICENSE). Protocol details are documented in the
[OpenRazer Barracuda X Chroma support discussion](https://github.com/openrazer/openrazer/issues/2704),
including the battery/charging events and October 2026 GET request captures.
This is an independent community plugin, with no affiliation with Razer.

## Omarchy Plugins listing

- **Name:** Barracuda Battery
- **Plugin ID:** `cody.barracuda-battery`
- **Category:** Hardware
- **Tags:** `bar`, `power-management`, `quickshell`
- **Repository:** https://github.com/costerou/barracudabattery
- **Maintainer note:** Manual setup is required for the model-specific udev
  access rule; Python 3 is an external runtime dependency.

The repository includes a root manifest, README, and MIT license. Before
submission, publish these files and ensure the repository is public. An
optional listing preview must be a root-level `preview.png`, `preview.jpg`,
`preview.jpeg`, `preview.webp`, or `preview.avif`; the icon above is not a
listing screenshot.

See the [publishing guide](https://plugins.omarchy.org/publish.html) and
[submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml).
Listing approval is separate from installation and is not a security audit.
