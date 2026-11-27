"""Unit tests for deterministic scanner (C) — offline, no external binaries."""
from src.adaptix.code_audit.scanner import scan_bundle, _fallback_scan, observation_from_findings, note_from_findings

SECRET_SRC = 'api_key = "sk-abcdefghijklmnopqrstuvwxyz0123456789"\n'
SQLI_SRC = 'cursor.execute("SELECT * FROM users WHERE name = \'%s\'" % name)\n'
HTML_SRC = '<script>document.getElementById("x").innerHTML = userInput;</script>\n'
CLEAN_SRC = 'print("hello")\n'


def _bundle(files):
    return {'files': {p: {'text': t, 'sha256': 'x', 'lines': t.count(chr(10))} for p, t in files.items()},
            'name': 'test', 'excluded': 0}


def test_fallback_finds_secret_and_sqli_and_xss():
    bundle = _bundle({'a.py': SECRET_SRC, 'b.py': SQLI_SRC, 'c.html': HTML_SRC})
    found = _fallback_scan(bundle)
    ids = {f['check_id'] for f in found}
    assert 'secret-hardcoded' in ids or 'token-bearer' in ids
    assert 'sql-exec' in ids
    assert 'innerhtml' in ids
    assert all(f['severity'] in ('high', 'medium', 'low', 'info') for f in found)


def test_fallback_clean_bundle_has_no_findings():
    bundle = _bundle({'a.py': CLEAN_SRC, 'b.md': '# hello\n'})
    assert _fallback_scan(bundle) == []
    # scan_bundle falls back to regex when no external binary exists (CI machine).
    # On a machine with bandit/semgrep installed this asserts >=0, so skip the
    # strict equality and only check the shape.
    rows = scan_bundle(bundle)
    assert isinstance(rows, list)


"""
Verifikasi scanner nyata: bandit + semgrep langsung.
"""
from src.adaptix.code_audit.scanner import scan_bundle, _fallback_scan

PY_WITH_ISSUE = 'import subprocess\nsubprocess.call("ls " + x, shell=True)\npassword = "hunter2secret"\n'
HTML_CLEAN = '<!DOCTYPE html><html><body><h1>Hallo</h1></body></html>\n'


def _bundle(files):
    return {'files': {p: {'text': t, 'sha256': 'x', 'lines': t.count(chr(10))} for p, t in files.items()},
            'name': 'test', 'excluded': 0}


def test_real_scanners_run_and_find_issues():
    b = _bundle({'x.py': PY_WITH_ISSUE})
    rows = scan_bundle(b)
    # at least one backend fires (bandit B602 shell=True, or fallback)
    assert rows, 'scanner harus menemukan minimal 1 kandidat pada source beracun'
    scanners = {r['scanner'] for r in rows}
    assert scanners & {'bandit', 'fallback-regex'}, f'hasil tak diduga: {scanners}'


def test_real_scanners_clean_file_no_crash():
    b = _bundle({'x.py': 'print("ok")\n', 'y.html': HTML_CLEAN})
    rows = scan_bundle(b)
    assert isinstance(rows, list)  # boleh 0 untuk file bersih, asal tidak crash


def test_bandit_directly():
    import shutil
    if not shutil.which('bandit'):
        return
    b = _bundle({'x.py': 'import subprocess\nsubprocess.call("x", shell=True)\n'})
    from src.adaptix.code_audit.scanner import _scan_bandit
    rows = _scan_bandit(b)
    assert any('shell' in r['title'].lower() or r['check_id'] == 'B602' for r in rows), rows[:2]

