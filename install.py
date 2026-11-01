#!/usr/bin/env python3
"""Install plugin and place it immediately after the tray; preserve other settings."""
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

source = Path(__file__).resolve().parent
config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'omarchy'
plugin = config / 'plugins/cody.barracuda-battery'
# Complete dependency/privilege steps before touching the bar.
subprocess.run(['sudo', 'install', '-m', '644', str(source / '70-barracuda-battery.rules'),
                '/etc/udev/rules.d/70-barracuda-battery.rules'], check=True)
subprocess.run(['sudo', 'udevadm', 'control', '--reload-rules'], check=True)
subprocess.run(['sudo', 'udevadm', 'trigger', '--action=add', '--subsystem-match=hidraw'], check=True)
subprocess.run(['udevadm', 'settle'], check=True)
shutil.copytree(source / 'plugin', plugin, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__'))
path = config / 'shell.json'
data = json.loads(path.read_text()) if path.exists() else {'version': 1}
layout = data.setdefault('bar', {}).setdefault('layout', {})
if not any(entry.get('id') == 'cody.barracuda-battery'
           for section in layout.values() if isinstance(section, list) for entry in section):
    right = layout.setdefault('right', [])
    index = next((i + 1 for i, entry in enumerate(right) if entry.get('id') == 'omarchy.tray'), 0)
    right.insert(index, {'id': 'cody.barracuda-battery'})
    if path.exists():
        backup = path.with_name('shell.json.barracuda-backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copy2(path, backup)
        print('Config backup:', backup)
    temporary = path.with_suffix('.barracuda.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)
subprocess.run(['omarchy-shell', 'shell', 'rescanPlugins'], check=True)
print('Installed:', plugin)
