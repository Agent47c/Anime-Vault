"""Verify a built Windows payload without installing it or using a real profile."""
import argparse
import json
import os
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, default=ROOT/'dist'/'AnimeVault')
    parser.add_argument('--report', type=Path, default=ROOT/'data'/'frozen-package-check.json')
    args = parser.parse_args()
    executable = args.payload.resolve()/'AnimeVault.exe'
    if not executable.is_file():
        parser.error('Standalone executable not found: '+str(executable))
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'OFFLINE_MODE': 'true', 'APP_PROFILE': '0', 'QT_QPA_PLATFORM': 'offscreen'}
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    env['PATH'] = os.pathsep.join([str(windows/'System32'), str(windows)])
    for key in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONUSERBASE', 'VIRTUAL_ENV'):
        env.pop(key, None)
    result = subprocess.run([str(executable), '--self-test', str(report)], env=env, timeout=120,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if not report.is_file():
        raise RuntimeError(f'The executable exited ({result.returncode}) before writing its smoke report.')
    smoke = json.loads(report.read_text(encoding='utf-8'))
    if result.returncode != 0 or not smoke.get('ok') or not smoke.get('frozen'):
        raise RuntimeError('Packaged smoke check failed: '+json.dumps(smoke))
    with tempfile.TemporaryDirectory(prefix='AnimeVault-chrome-check-') as directory:
        message = json.dumps({'action': 'fixture'}).encode()
        result = subprocess.run([str(executable), '--native-magnet-host', 'chrome-extension://'+'a'*32+'/'],
                                input=struct.pack('<I',len(message))+message, capture_output=True,
                                env={**env, 'ANIMEVAULT_DATA_DIR': directory}, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if len(result.stdout) < 4:
            raise RuntimeError('Packaged Chrome host did not return framed JSON on its inherited pipe.')
        size = struct.unpack('<I', result.stdout[:4])[0]
        response = json.loads(result.stdout[4:4+size])
        if response.get('ok') is not False or result.returncode != 1:
            raise RuntimeError('Unregistered fixture browser was not rejected correctly.')
    smoke['checks'].append('Windowed Chrome host returns framed JSON and rejects an unregistered caller')
    smoke['checks'].append('Standalone launch with Python/virtual-environment paths removed')
    report.write_text(json.dumps(smoke,indent=2),encoding='utf-8')
    print(json.dumps(smoke,indent=2))


if __name__ == '__main__':
    main()
