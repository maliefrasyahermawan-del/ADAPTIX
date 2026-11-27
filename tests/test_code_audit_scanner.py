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


def test_observation_and_note_shape():
    bundle = _bundle({'a.py': SECRET_SRC})
    found = _fallback_scan(bundle)
    assert found
    obs = observation_from_findings(found, bundle)
    assert obs['tool'] == 'deterministic_scan'
    assert obs['status'] == 'observed'
    assert obs['data']['scanner_findings']
    note = note_from_findings(found)
    assert 'Scanner deterministik' in note
    assert str(len(found)) in note
