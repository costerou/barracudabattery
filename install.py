#!/usr/bin/env python3
"""Install plugin and place it immediately after the tray; preserve other settings."""
import datetime
import json
import os
from pathlib import Path
import shutil
import stat
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
# The repository keeps a single root manifest; adapt its entry point for the flat copy.
manifest = json.loads((source / 'manifest.json').read_text())
manifest['entryPoints'] = {kind: Path(entry).name for kind, entry in manifest['entryPoints'].items()}
(plugin / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
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
    # Keep the existing file mode (new files default to owner-only) so private
    # settings are never exposed by the rewrite, regardless of umask.
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    temporary = path.with_suffix('.barracuda.tmp')
    temporary.unlink(missing_ok=True)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w') as handle:
            fd = None
            handle.write(json.dumps(data, indent=2) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        if fd is not None:
            os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
subprocess.run(['omarchy-shell', 'shell', 'rescanPlugins'], check=True)
print('Installed:', plugin)
