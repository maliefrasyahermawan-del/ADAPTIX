"""Deterministic scanner pre-pass for static code audit.

Runs before any LLM call, so the model does not have to discover with
regex/AST what a scanner can find in <5s. Each backend is a subprocess
( bandit / semgrep / osv-scanner / gitleaks ) detected by shutil.which;
when none is installed we fall back to an in-process regex sweep over
the sanitized bundle text (BOM/secret/high-risk pattern). Results are
therefore never empty for a non-empty bundle, and the engine seeds the
first LLM payload with the summary.

Output shape (verified findings): dict(title, severity, evidence_ids, ...)
— but evidence_ids cannot point to read_source observations yet, so the
engine merges them with verification_status='verified' separately.
Here we return scanner rows in the same shape the LLM report expects;
evidence is a synthetic read_source-free record the UI renders as-is.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def _severity_map(level: str) -> str:
    level = (level or '').lower()
    if level in ('critical', 'high'):
        return 'high'
    if level in ('medium', 'moderate'):
        return 'medium'
    if level in ('low', 'info', 'informational'):
        return 'low'
    return 'info'


# In-process fallback patterns: (check_id, title, severity, CWE, regex)
_FALLBACK_PATTERNS = [
    ('secret-hardcoded', 'Kredensial hardcoded di source',
     'high', 'CWE-798',
     re.compile(r'(?i)(?:api[_-]?key|password|passwd|secret|access[_-]?token)\b\s*[:=]\s*["\'][^"\']{8,}["\']')),
    ('token-bearer', 'Bearer token hardcoded',
     'high', 'CWE-798',
     re.compile(r'\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|AIza[A-Za-z0-9_-]{10,})')),
    ('sql-exec', 'Eksekusi SQL dinamis (injection risk)',
     'medium', 'CWE-89',
     re.compile(r'(?i)(?:execute|executemany|query|raw)\s*\([^)]*(?:\+|%s|%\(|format\(|f["\'])')),
    ('eval-exec', 'eval/exec pada input (code injection)',
     'high', 'CWE-94',
     re.compile(r'\b(?:eval\s*\(|exec\s*\(|Function\s*\()')),
    ('subprocess-shell', 'subprocess dengan shell=True',
     'medium', 'CWE-78',
     re.compile(r'shell\s*=\s*True|shellexecute\s*\(')),
    ('innerhtml', 'innerHTML dengan data pengguna (XSS risk)',
     'medium', 'CWE-79',
     re.compile(r'innerHTML\s*=|document\.write|outerHTML\s*=')),
    ('localstorage-sensitive', 'Data sensitif di localStorage',
     'medium', 'CWE-922',
     re.compile(r'(?i)localStorage\s*\.\s*setItem\s*\([^,]*?(?:token|password|secret|api[_-]?key|email|nik|ktp)')),
    ('hardcoded-url-key', 'URL dengan API key di query',
     'medium', 'CWE-598',
     re.compile(r'https?://[^\s"\'<>]+(?:api[_-]?key|token|secret)=[^\s"\'&<>]+', re.I)),
]


def _fallback_scan(bundle) -> list[dict]:
    """Regex sweep over bundle['files'][path]['text'] — runs offline, no deps."""
    findings: list[dict] = []
    files = bundle.get('files') or {}
    for path, row in sorted(files.items()):
        text = row.get('text') or ''
        lines = text.splitlines()
        for check_id, title, severity, cwe, pattern in _FALLBACK_PATTERNS:
            for lineno, line in enumerate(lines, start=1):
                if pattern.search(line):
                    findings.append({
                        'title': f'{title} — {path}:{lineno}',
                        'severity': severity,
                        'evidence_ids': [],
                        'description': f'Ditemukan pola {check_id} pada {path} baris {lineno}. '
                                        f'Snippet: {line.strip()[:200]}',
                        'impact': 'Perlu tinjauan manual; pola ini adalah sinyal awal, bukan bukti eksploitasi.',
                        'remediation': 'Pindahkan kredensial ke env/secret store; validasi & escape input; '
                                        'gunakan parameter binding untuk query.',
                        'cwe': cwe,
                        'scanner': 'fallback-regex',
                        'path': path,
                        'line': lineno,
                        'check_id': check_id,
                    })
                    break  # one hit per pattern per file is enough
    # secrets aggregated from bundle redact() leftovers
    secret_hits = [f for f in findings if f['check_id'] in ('secret-hardcoded', 'token-bearer')]
    if secret_hits:
        findings.append({
            'title': f'Ringkasan: {len(secret_hits)} indikasi kredensial hardcoded',
            'severity': 'high',
            'evidence_ids': [],
            'description': f'{len(secret_hits)} file/baris match pola kredensial. '
                            'Nilai sebenarnya sudah di-redact di bundle; temuan ini merujuk ke lokasi, bukan nilai.',
            'impact': 'Kredensial di client-side dapat bocor ke siapa pun yang membaca source.',
            'remediation': 'Rotasi kredensial, pindahkan ke server-side secret store.',
            'cwe': 'CWE-798', 'scanner': 'fallback-regex', 'path': '', 'line': 0,
            'check_id': 'secret-summary',
        })
    return findings


def _run_subprocess(argv, timeout=120):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return out
    except (OSError, subprocess.TimeoutExpired):
        return None


def _resolve(name: str, cfg_cmd: str) -> str | None:
    """vendor/bin dulu, lalu PATH. config/scanners.yaml bisa override command."""
    import os
    from pathlib import Path as _P

    # config override
    if cfg_cmd and cfg_cmd != name:
        p = _P(cfg_cmd)
        if p.is_absolute() or (p.parent != _P('.')):
            # explicit path (e.g. vendor/bin/gitleaks.exe)
            if p.is_file():
                return str(p)
    # vendor/bin/<name>.exe (repo-bundled, checksum verified)
    root = _P(__file__).resolve().parents[3]
    vendor = root / 'vendor' / 'bin' / (name + '.exe')
    if vendor.is_file():
        return str(vendor)
    found = shutil.which(name)
    if found:
        return found
    # also try without .exe suffix on Windows
    if os.name == 'nt':
        return shutil.which(name + '.exe')
    return None


_SCANNER_CONFIG = None


def _load_config():
    global _SCANNER_CONFIG
    if _SCANNER_CONFIG is not None:
        return _SCANNER_CONFIG
    try:
        from src.adaptix.config import config as _cfg
        _SCANNER_CONFIG = _cfg('scanners.yaml') or {}
    except Exception:
        _SCANNER_CONFIG = {}
    return _SCANNER_CONFIG


def _scanner_enabled(name: str) -> bool:
    cfg = _load_config()
    block = (cfg.get('scanners') or {}).get(name) or {}
    return bool(block.get('enabled', True))


def _scanner_cmd(name: str) -> str:
    cfg = _load_config()
    block = (cfg.get('scanners') or {}).get(name) or {}
    return str(block.get('command') or name)


def _scanner_timeout(name: str, default: int) -> int:
    cfg = _load_config()
    block = (cfg.get('scanners') or {}).get(name) or {}
    try:
        return int(block.get('timeout_seconds') or default)
    except (TypeError, ValueError):
        return default


def _scan_bandit(bundle) -> list[dict]:
    """bandit -r <tmpdir> -f json — Python SAST."""
    if not _scanner_enabled('bandit'):
        return []
    cmd = _resolve('bandit', _scanner_cmd('bandit'))
    if not cmd:
        return []
    files = bundle.get('files') or {}
    tmp = tempfile.mkdtemp(prefix='bandit-')
    root = Path(tmp)
    try:
        for rel, row in files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(row.get('text') or '', encoding='utf-8')
        out = _run_subprocess([cmd, '-r', str(root), '-f', 'json', '-o', str(root / 'out.json'),
                               '--quiet'], timeout=_scanner_timeout('bandit', 180))
        if out is None or not (root / 'out.json').is_file():
            return []
        import json
        data = json.loads((root / 'out.json').read_text(encoding='utf-8'))
        rows = []
        for issue in (data.get('results') or []):
            rows.append({
                'title': f"{issue.get('test_name', 'bandit')} — {issue.get('filename', '')}:{issue.get('line_number', '')}",
                'severity': _severity_map(issue.get('issue_severity', 'info')),
                'evidence_ids': [],
                'description': issue.get('issue_text', '')[:2000],
                'impact': 'Temuan SAST deterministik Bandit; perlu validasi konteks bisnis.',
                'remediation': issue.get('more_info', '')[:2000] or 'Lihat dokumentasi CWE pada more_info.',
                'cwe': str(issue.get('cwe', {}).get('id') or '') if isinstance(issue.get('cwe'), dict) else '',
                'scanner': 'bandit', 'path': str(issue.get('filename') or ''),
                'line': int(issue.get('line_number') or 0),
                'check_id': str(issue.get('test_id') or ''),
            })
        return rows
    except Exception:
        return []
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)


def _scan_semgrep(bundle) -> list[dict]:
    """semgrep scan --config p/ci --json — multi-language SAST."""
    if not _scanner_enabled('semgrep'):
        return []
    cmd = _resolve('semgrep', _scanner_cmd('semgrep'))
    if not cmd:
        return []
    files = bundle.get('files') or {}
    tmp = tempfile.mkdtemp(prefix='semgrep-')
    root = Path(tmp)
    try:
        for rel, row in files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(row.get('text') or '', encoding='utf-8')
        _semgrep_cfg = (_scanner_cmd('semgrep') == 'semgrep' and 'p/ci') or 'p/ci'
        out = _run_subprocess([cmd, 'scan', '--config', _semgrep_cfg, '--json',
                               '--metrics=off', '--quiet', str(root)], timeout=_scanner_timeout('semgrep', 180))
        if out is None or not out.stdout:
            return []
        import json
        data = json.loads(out.stdout)
        rows = []
        for hit in (data.get('results') or []):
            rows.append({
                'title': f"{hit.get('check_id', 'semgrep')} — {hit.get('path', '')}:{hit.get('start', {}).get('line', '')}",
                'severity': _severity_map(hit.get('extra', {}).get('severity', 'info')),
                'evidence_ids': [],
                'description': (hit.get('extra', {}).get('message', '') or '')[:2000],
                'impact': 'Temuan SAST deterministik Semgrep; perlu validasi konteks bisnis.',
                'remediation': (hit.get('extra', {}).get('fix', '') or '')[:2000] or 'Ikuti panduan rule Semgrep.',
                'cwe': '',
                'scanner': 'semgrep', 'path': str(hit.get('path') or ''),
                'line': int(hit.get('start', {}).get('line') or 0),
                'check_id': str(hit.get('check_id') or ''),
            })
        return rows
    except Exception:
        return []
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)


def _scan_gitleaks(bundle) -> list[dict]:
    """gitleaks detect --no-git --source <tmpdir> --report-format json."""
    if not _scanner_enabled('gitleaks'):
        return []
    cmd = _resolve('gitleaks', _scanner_cmd('gitleaks'))
    if not cmd:
        return []
    files = bundle.get('files') or {}
    tmp = tempfile.mkdtemp(prefix='gitleaks-')
    root = Path(tmp)
    try:
        for rel, row in files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(row.get('text') or '', encoding='utf-8')
        report = root / 'g.json'
        out = _run_subprocess([cmd, 'detect', '--no-git', '--source', str(root),
                               '--report-format', 'json', '--report-path', str(report),
                               '--verbose'], timeout=_scanner_timeout('gitleaks', 120))
        if not report.is_file():
            return []
        import json
        data = json.loads(report.read_text(encoding='utf-8'))
        rows = []
        for leak in (data or []):
            rows.append({
                'title': f"Secret terdeteksi ({leak.get('RuleID', '')}) — {leak.get('File', '')}:{leak.get('StartLine', '')}",
                'severity': 'high',
                'evidence_ids': [],
                'description': (leak.get('Description') or '')[:2000],
                'impact': 'Secret di source dapat bocor; anggap sudah diketahui publik.',
                'remediation': 'Cabut & rotasi secret, pindahkan ke secret manager.',
                'cwe': 'CWE-798', 'scanner': 'gitleaks',
                'path': str(leak.get('File') or ''), 'line': int(leak.get('StartLine') or 0),
                'check_id': str(leak.get('RuleID') or ''),
            })
        return rows
    except Exception:
        return []
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)


def _scan_osv(bundle) -> list[dict]:
    """osv-scanner scan source -r <tmpdir> --format json — dependency vuln."""
    if not _scanner_enabled('osv-scanner'):
        return []
    cmd = _resolve('osv-scanner', _scanner_cmd('osv-scanner'))
    if not cmd:
        return []
    files = bundle.get('files') or {}
    tmp = tempfile.mkdtemp(prefix='osv-')
    root = Path(tmp)
    try:
        for rel, row in files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(row.get('text') or '', encoding='utf-8')
        out = _run_subprocess([cmd, 'scan', 'source', '-r', str(root),
                               '--format', 'json', '--skip-go'], timeout=_scanner_timeout('osv-scanner', 180))
        if out is None or not out.stdout:
            return []
        import json
        data = json.loads(out.stdout)
        rows = []
        for pkg in (data.get('results') or []):
            for vuln in (pkg.get('vulns') or []):
                rows.append({
                    'title': f"{vuln.get('id', 'OSV')} — {pkg.get('package', {}).get('name', '')}",
                    'severity': _severity_map(
                        str((vuln.get('severity') or [{}])[0].get('score', ''))[:1] if vuln.get('severity') else 'high'),
                    'evidence_ids': [],
                    'description': (vuln.get('summary') or vuln.get('details') or '')[:2000],
                    'impact': 'Dependensi rentan menurut OSV; upgrade ke versi perbaikan.',
                    'remediation': 'Upgrade package ke versi minimum fixed.',
                    'cwe': '',
                    'scanner': 'osv-scanner',
                    'path': str(pkg.get('source', '')), 'line': 0,
                    'check_id': str(vuln.get('id') or ''),
                })
        return rows
    except Exception:
        return []
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)


def scan_bundle(bundle) -> list[dict]:
    """Run every available scanner; fall back to regex if none installed.

    Order dari config/scanners.yaml (default: bandit -> semgrep -> gitleaks -> osv-scanner).
    External scanners only run when their binary is on PATH or vendor/bin/,
    so the audit works on a plain `pip install` machine too.
    """
    cfg = _load_config()
    order = cfg.get('order') or ['bandit', 'semgrep', 'gitleaks', 'osv-scanner']
    backend_by_name = {
        'bandit': _scan_bandit, 'semgrep': _scan_semgrep,
        'gitleaks': _scan_gitleaks, 'osv-scanner': _scan_osv,
    }
    findings: list[dict] = []
    for name in order:
        backend = backend_by_name.get(name)
        if backend is None:
            continue
        try:
            found = backend(bundle)
        except Exception:
            found = []
        findings.extend(found)
    if not findings:
        findings = _fallback_scan(bundle)
    # dedupe by (check_id, path, line)
    seen = set()
    unique = []
    for row in findings:
        key = (row.get('check_id'), row.get('path'), row.get('line'))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique[:200]


def observation_from_findings(findings, bundle) -> dict:
    """Wrap scanner findings into an engine observation (verified candidate)."""
    import hashlib, json, secrets, time
    payload = {
        'scanner_findings': findings,
        'files_scanned': len(bundle.get('files') or {}),
    }
    return {
        'tool': 'deterministic_scan',
        'target': bundle.get('name') or '',
        'sha256': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        'data': payload,
        'id': 'obs-' + secrets.token_hex(6),
        'status': 'observed',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }


def note_from_findings(findings) -> str:
    if not findings:
        return 'Scanner deterministik: tidak ada kandidat pola rentan pada bundle.'
    by_scanner = {}
    for row in findings:
        by_scanner[row.get('scanner', '?')] = by_scanner.get(row.get('scanner', '?'), 0) + 1
    parts = ', '.join(f'{k}: {v}' for k, v in sorted(by_scanner.items()))
    return (f'Scanner deterministik menemukan {len(findings)} kandidat '
            f'terverifikasi awal ({parts}). Kandidat ini ada di observasi pertama; '
            'fokuskan read_source pada baris/path tersebut dan nilai konteksnya '
            'sebelum menulis laporan. Jangan mengulang pencarian pola yang sudah '
            'diverifikasi scanner.')


# aliases used by engine
_scanner_observation = observation_from_findings
_scanner_note = note_from_findings
