import json
from types import SimpleNamespace

import pytest

from src.adaptix.code_audit.engine import run_audit
from src.adaptix.code_audit.schema import Action
from src.adaptix.code_audit.sources import write_bundle


SOURCE = '''import sqlite3\n\ndef lookup(name):\n    db = sqlite3.connect("app.db")\n    cursor = db.cursor()\n    cursor.execute("SELECT * FROM users WHERE name = '%s'" % name)\n    return cursor.fetchall()\n'''


def _zip():
    import io
    import zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('app.py', SOURCE)
    return buffer.getvalue()


def _response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10, total_tokens=20),
    )


def _observation_id(messages):
    payload = json.loads(messages[-1]['content'])
    return payload['observation_summaries'][-1]['id']


def test_model_loop_writes_evidence_bound_report(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Lihat katalog source.',
                'action': {'tool': 'list_source', 'arguments': {}}}))
        if calls['n'] == 2:
            return _response(json.dumps({
                'commentary': 'Baca app.py.',
                'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}}))
        obs = _observation_id(kwargs['messages'])
        return _response(json.dumps({
            'commentary': 'Laporan selesai.',
            'report': {
                'title': 'SQL injection pada lookup',
                'executive_summary': 'Parameter name dirangkai ke query.',
                'methodology': 'Membaca app.py.',
                'findings': [{
                    'title': 'SQL injection',
                    'severity': 'high',
                    'evidence_ids': [obs],
                    'description': 'Query dirangkai dengan % sehingga input masuk ke SQL.',
                    'impact': 'Pembacaan data arbitrer.',
                    'remediation': 'Gunakan parameterized query.',
                    'cwe': 'CWE-89',
                }],
                'limitations': 'Hanya analisis statis.',
                'next_steps': 'Verifikasi dinamis di lab.',
            }}))

    state = run_audit(run_dir, 'Cari kerentanan', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=6, call=call)
    assert state['status'] == 'completed'
    record = json.loads((run_dir / 'code-report.json').read_text(encoding='utf-8'))
    finding = record['findings'][0]
    assert finding['severity'] == 'high'
    assert finding['verification_status'] == 'model_assessed'
    assert finding['independently_verified'] is False
    assert finding['evidence'][0]['tool'] == 'read_source'
    assert (run_dir / 'code-report.md').is_file()


def test_fabricated_evidence_is_rejected(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Baca.',
                'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}}))
        return _response(json.dumps({
            'commentary': 'Laporan.',
            'report': {
                'title': 'Temuan', 'executive_summary': 'x', 'methodology': 'y',
                'findings': [{'title': 'x', 'severity': 'high',
                              'evidence_ids': ['obs-deadbeef'],
                              'description': 'x', 'impact': 'x', 'remediation': 'x'}],
                'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=6, call=call)
    assert state['status'] == 'completed_with_errors'
    assert state['stop_reason'] == 'invalid_report'
    assert not (run_dir / 'code-report.json').exists()


def test_provider_failure_does_not_fake_a_report(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')

    def call(**kwargs):
        raise RuntimeError('provider down')

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=3, call=call)
    assert state['status'] == 'completed_with_errors'
    assert state['stop_reason'] == 'provider_unavailable'
    assert not (run_dir / 'code-report.json').exists()


def test_network_and_terminal_actions_are_not_in_the_schema():
    for name in ('http_request', 'browser_observe', 'terminal', 'file'):
        with pytest.raises(Exception):
            Action.model_validate({'tool': name, 'arguments': {}})


def test_provider_rejecting_reasoning_effort_is_retried_without_it(monkeypatch):
    import litellm
    import src.adaptix.code_audit.engine as engine
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if 'reasoning_effort' in kwargs:
            raise RuntimeError(
                "openai does not support parameters: ['reasoning_effort']")
        return {'ok': True}

    monkeypatch.setattr(litellm, 'completion', fake_completion)
    monkeypatch.setenv('ADAPTIX_REASONING_EFFORT', 'none')
    result = engine._provider_call(
        [{'role': 'user', 'content': 'x'}], model='openai/test/model',
        api_base=None, api_key=None, max_tokens=10, timeout=5)
    assert result == {'ok': True}
    assert len(calls) == 2
    assert 'reasoning_effort' not in calls[1]
