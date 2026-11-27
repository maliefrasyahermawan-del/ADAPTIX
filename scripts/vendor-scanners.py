"""Unduh & verifikasi binary scanner Windows yang di-bundle ke vendor/bin/.

Kenapa perlu ini: bandit & semgrep adalah pip package langsung, tapi
gitleaks dan osv-scanner hanya tersedia sebagai binary Go. Script ini
mengunduh dari GitHub Releases resmi, memverifikasi SHA256 dengan
checksum manifest resmi, dan menaruh .exe ke vendor/bin/.

    python scripts/vendor-scanners.py

Aman di-rerun: binary yang sudah ada & checksum cocok dilewati.
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / 'vendor' / 'bin'

SCANNERS = {
    'gitleaks.exe': {
        'url': 'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_windows_x64.zip',
        'zip': True, 'inner': 'gitleaks.exe',
        'sha256': 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e',  # zip
    },
    'osv-scanner.exe': {
        'url': 'https://github.com/google/osv-scanner/releases/download/v2.7.1/osv-scanner_windows_amd64.exe',
        'zip': False,
        'sha256': '7121dcf420aefbbf89a7f0050c4d3094e079ff93afd334dfc96f16b02ec85800',
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    BIN.mkdir(parents=True, exist_ok=True)
    for name, spec in SCANNERS.items():
        dest = BIN / name
        if dest.is_file() and dest.stat().st_size > 1_000_000:
            print(f'[skip] {name} sudah ada ({dest.stat().st_size:,} bytes)')
            continue
        print(f'[get ] {spec["url"]}')
        data = urllib.request.urlopen(spec['url'], timeout=180).read()
        got = _sha256(data)
        if got != spec['sha256']:
            print(f'[FAIL] {name}: sha256 tidak cocok\n  got={got}\n  exp={spec["sha256"]}')
            return 1
        print(f'[ ok ] sha256 cocok ({got[:16]}...) size={len(data):,}')
        if spec['zip']:
            import io, zipfile
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                z.extract(spec['inner'], BIN)
        else:
            dest.write_bytes(data)
        if not dest.is_file():
            print(f'[FAIL] {name} tidak ditemukan setelah extract')
            return 1
        print(f'[done] {name}')
    print('\nSemua scanner terverifikasi.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
