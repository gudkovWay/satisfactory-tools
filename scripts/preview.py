#!/usr/bin/env python3
"""Finite Nuxt and installed headless Chromium session inside guarded-run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

sys.path.insert(0, '/home/q/.config/worktrunk/projects')
from resource_guard import assert_guarded, reserve_environment

ROOT = Path(__file__).resolve().parents[1]


def terminate(process):
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def stop_signal(_signal, _frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=480)
    parser.add_argument('--static-root', type=Path, help='Serve an existing generated public directory instead of Nuxt dev.')
    parser.add_argument('--software-webgl', action='store_true', help='Render WebGL with SwiftShader in the owned headless profile, without using the hardware GPU.')
    parser.add_argument('--fine-pointer', action='store_true', help='Expose a virtual fine pointer and hover capability in the owned headless browser.')
    args = parser.parse_args()
    if not 60 <= args.seconds <= 540:
        parser.error('duration must be60..540seconds')
    assert_guarded()
    reserve_environment(ROOT)
    chromium, private_bus = shutil.which('chromium'), shutil.which('dbus-run-session')
    if not chromium or not private_bus:
        raise RuntimeError('Installed Chromium and dbus-run-session are required; no automatic installation.')
    static_root = args.static_root.resolve() if args.static_root else None
    if static_root:
        if not (static_root / 'index.html').is_file():
            raise RuntimeError('Static preview requires an existing generated index.html.')
    elif not (ROOT / 'node_modules/nuxt/bin/nuxt.mjs').is_file() or not (ROOT / '.nuxt/tsconfig.app.json').is_file():
        raise RuntimeError('Install the pinned dependencies and run the addressed Nuxt prepare first.')
    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)
    deadline = time.monotonic() + args.seconds
    artifacts = ROOT / '.superpowers/assets' / f'nuxt-preview-{os.getpid()}'
    artifacts.mkdir(parents=True)
    stop_file = artifacts / 'stop'
    with socket.socket() as allocation:
        allocation.bind(('127.0.0.1', 0))
        port = allocation.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    source_files = [ROOT / 'package.json', ROOT / 'package-lock.json', ROOT / 'nuxt.config.ts', ROOT / 'tsconfig.json']
    source_files += [file for directory in ('app', 'shared', 'public', 'scripts') for file in (ROOT / directory).rglob('*') if file.is_file()]
    source_files += [ROOT / 'factory.py', *sorted((ROOT / 'satisfactory').glob('*.py'))]
    source_hashes = {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest() for file in source_files}
    manifest = {'url': url, 'artifacts': str(artifacts), 'stop_file': str(stop_file), 'cgroup': Path('/proc/self/cgroup').read_text().strip(), 'deadline_seconds': args.seconds, 'source_hashes': source_hashes}
    manifest['renderer_profile'] = 'software-webgl' if args.software_webgl else 'default-headless'
    manifest['pointer_profile'] = 'fine-hover' if args.fine_pointer else 'platform-default'
    if static_root:
        manifest['static_root'] = str(static_root)
        manifest['output_hashes'] = {str(file.relative_to(static_root)): hashlib.sha256(file.read_bytes()).hexdigest()
                                     for file in static_root.rglob('*') if file.is_file()}
    server = browser = None
    with tempfile.TemporaryDirectory(prefix='omp-factory-nuxt-') as temporary:
        private = Path(temporary)
        directories = {name: private / name for name in ('home', 'config', 'data', 'state', 'cache', 'runtime', 'browser')}
        for directory in directories.values():
            directory.mkdir(mode=0o700)
        bus_config = private / 'bus.conf'
        bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir=' + str(directories['runtime']) + '</listen><auth>EXTERNAL</auth><policy context="default"><allow user="' + str(os.getuid()) + '"/><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
        removed = {'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS', 'DBUS_STARTER_ADDRESS', 'DBUS_STARTER_BUS_TYPE', 'DBUS_SYSTEM_BUS_ADDRESS', 'AT_SPI_BUS_ADDRESS', 'HYPRLAND_INSTANCE_SIGNATURE'}
        environment = {key: value for key, value in os.environ.items() if key not in removed}
        environment.update(HOME=str(directories['home']), XDG_CONFIG_HOME=str(directories['config']), XDG_DATA_HOME=str(directories['data']), XDG_STATE_HOME=str(directories['state']), XDG_CACHE_HOME=str(directories['cache']), XDG_RUNTIME_DIR=str(directories['runtime']), NUXT_TELEMETRY_DISABLED='1', NUXT_IGNORE_UPDATE_CHECK='1', NUXT_TUI='plain')
        try:
            with (artifacts / 'server.log').open('w') as server_log, (artifacts / 'browser.log').open('w') as browser_log:
                command = ([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(static_root)]
                           if static_root else ['node', 'node_modules/nuxt/bin/nuxt.mjs', 'dev', '--host', '127.0.0.1', '--port', str(port), '--strictPort', '--no-tui', '--no-fork', '--no-takeover'])
                server = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True)
                while True:
                    if server.poll() is not None:
                        raise RuntimeError('Nuxt exited during startup; inspect owned server.log.')
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Preview deadline elapsed during Nuxt startup.')
                    try:
                        with urlopen(url, timeout=3) as response:
                            if response.status == 200:
                                break
                    except HTTPError as exc:
                        if exc.code >= 500 and exc.code != 503:
                            raise RuntimeError('Nuxt returned a source/startup error; inspect owned server.log.') from exc
                    except (URLError, TimeoutError):
                        pass
                    time.sleep(.2)
                render_flags = (['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
                                if args.software_webgl else ['--disable-gpu'])
                pointer_flags = (['--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4']
                                 if args.fine_pointer else [])
                browser = subprocess.Popen([private_bus, '--config-file=' + str(bus_config), '--', chromium, '--headless=new', *render_flags, *pointer_flags, '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + str(directories['browser']), '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-sync', '--disable-extensions', '--password-store=basic', url], cwd=ROOT, env=environment, stdout=browser_log, stderr=subprocess.STDOUT, start_new_session=True)
                endpoint = directories['browser'] / 'DevToolsActivePort'
                while not endpoint.is_file():
                    if browser.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError('Owned Chromium did not become ready; no automatic resource retry.')
                    time.sleep(.1)
                cdp_port = endpoint.read_text().splitlines()[0]
                manifest.update(cdp_url='http://127.0.0.1:' + cdp_port, server_pid=server.pid, browser_pid=browser.pid)
                (artifacts / 'session.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
                print('ATLAS_READY ' + json.dumps({key: value for key, value in manifest.items() if key not in {'source_hashes', 'output_hashes'}}, ensure_ascii=False), flush=True)
                while not stop_file.exists() and time.monotonic() < deadline:
                    if browser.poll() is not None or server.poll() is not None:
                        raise RuntimeError('An owned preview process exited during exercise.')
                    time.sleep(.2)
                if not stop_file.exists():
                    raise RuntimeError('Preview deadline expired without an explicit stop receipt.')
        finally:
            terminate(browser)
            terminate(server)
            manifest['closed'] = True
            cgroup = Path('/sys/fs/cgroup') / Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1].lstrip('/')
            manifest['resources'] = {name: (cgroup / name).read_text().strip() for name in ('memory.peak', 'memory.events', 'pids.peak') if (cgroup / name).exists()}
            (artifacts / 'session.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
