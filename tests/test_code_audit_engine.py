import json
from types import SimpleNamespace

import pytest

from src.adaptix.code_audit.engine import _message_payload, run_audit
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


def test_reasoning_effort_none_is_omitted(monkeypatch):
    import litellm
    import src.adaptix.code_audit.engine as engine
    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return {'ok': True}

    monkeypatch.setattr(litellm, 'completion', fake_completion)
    monkeypatch.setenv('ADAPTIX_REASONING_EFFORT', 'none')
    engine._provider_call([{'role': 'user', 'content': 'x'}], model='openai/test/model',
                          api_base=None, api_key=None, max_tokens=10, timeout=5)
    assert 'reasoning_effort' not in calls[0]


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
    monkeypatch.setenv('ADAPTIX_REASONING_EFFORT', 'low')
    result = engine._provider_call(
        [{'role': 'user', 'content': 'x'}], model='openai/test/model',
        api_base=None, api_key=None, max_tokens=10, timeout=5)
    assert result == {'ok': True}
    assert len(calls) == 2
    assert 'reasoning_effort' not in calls[1]


def test_auto_patch_writes_report_patch_to_local_folder(tmp_path):
    from src.adaptix.code_audit.sources import write_directory_bundle
    source = tmp_path / 'project' / 'dist'
    source.mkdir(parents=True)
    (source / 'app.py').write_text(
        "def lookup(name):\n    return db.execute(\"SELECT * FROM users WHERE name = '%s'\" % name)\n",
        encoding='utf-8')
    run_dir = tmp_path / 'run'
    bundle = write_directory_bundle(run_dir, source)
    search = 'db.execute("SELECT * FROM users WHERE name = \'%s\'" % name)'
    replacement = 'db.execute("SELECT * FROM users WHERE name = ?", (name,))'
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Baca app.py.',
                'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}}))
        obs = _observation_id(kwargs['messages'])
        return _response(json.dumps({
            'commentary': 'Laporan dan patch.',
            'report': {
                'title': 'SQL injection',
                'executive_summary': 'x', 'methodology': 'y',
                'findings': [{'title': 'SQLi', 'severity': 'high',
                              'evidence_ids': [obs], 'description': 'x',
                              'impact': 'x', 'remediation': 'x', 'cwe': 'CWE-89'}],
                'patches': [{'path': 'app.py', 'search': search,
                             'replace': replacement, 'rationale': 'parameterized'}],
                'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari dan patch', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=6, call=call, auto_patch=True)
    assert state['status'] == 'completed'
    assert 'WHERE name = ?' in (source / 'app.py').read_text(encoding='utf-8')
    assert state['patches']['applied_count'] == 1
    record = json.loads((run_dir / 'code-report.json').read_text(encoding='utf-8'))
    assert record['patches']['applied_count'] == 1
    assert (run_dir / 'patches' / 'backup' / 'app.py').is_file()
    applied = record['patches']['applied'][0]
    assert applied['line'] == 2
    assert 'name = ?' in applied['after']
    markdown = (run_dir / 'code-report.md').read_text(encoding='utf-8')
    assert 'baris 2' in markdown
    assert 'Sebelum:' in markdown and 'Sesudah:' in markdown


def test_rate_limit_is_retried_and_then_recovers(tmp_path, monkeypatch):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    calls = {'n': 0}
    monkeypatch.setenv('ADAPTIX_PROVIDER_RETRY_DELAY', '0.01')

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            raise RuntimeError('429 Too Many Requests: rate limited')
        return _response(json.dumps({
            'commentary': 'Tidak ada temuan.',
            'report': {
                'title': 'Audit', 'executive_summary': 'x', 'methodology': 'y',
                'findings': [], 'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=3, call=call)
    assert calls['n'] == 2
    assert state['status'] == 'completed'
    assert state['stop_reason'] == 'model_reported'


def test_persistent_rate_limit_reports_specific_stop_reason(tmp_path, monkeypatch):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    calls = {'n': 0}
    monkeypatch.setenv('ADAPTIX_PROVIDER_RETRY_DELAY', '0.01')

    def call(**kwargs):
        calls['n'] += 1
        raise RuntimeError('429 Too Many Requests: rate limited')

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=3, call=call)
    assert calls['n'] == 4
    assert state['status'] == 'completed_with_errors'
    assert state['stop_reason'] == 'provider_rate_limited'


def test_duplicate_read_is_blocked_and_model_can_finish(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Baca app.py.',
                'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}}))
        if calls['n'] == 2:
            return _response(json.dumps({
                'commentary': 'Baca ulang.',
                'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}}))
        if calls['n'] == 3:
            payload = json.loads(kwargs['messages'][-1]['content'])
            assert 'sudah dibaca' in payload['feedback']
            return _response(json.dumps({
                'commentary': 'Bukti cukup.',
                'report': {'title': 'Audit', 'executive_summary': 'x',
                           'methodology': 'y', 'findings': [],
                           'limitations': 'z', 'next_steps': 'z'}}))
        raise AssertionError('model should have finished')

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=6, call=call)
    assert state['status'] == 'completed'
    assert len(state['observations']) == 1


def _zip_with(path, text):
    import io
    import zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(path, text)
    return buffer.getvalue()


def test_overlapping_read_already_covered_is_blocked(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip_with('big.py', '\n'.join(
        f'line_{i} = {i}' for i in range(1, 301))), 'big.zip')
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Baca awal file.',
                'action': {'tool': 'read_source', 'arguments': {
                    'path': 'big.py', 'start_line': 1, 'limit': 200}}}))
        if calls['n'] == 2:
            return _response(json.dumps({
                'commentary': 'Baca ulang sebagian.',
                'action': {'tool': 'read_source', 'arguments': {
                    'path': 'big.py', 'start_line': 50, 'limit': 100}}}))
        payload = json.loads(kwargs['messages'][-1]['content'])
        assert 'sudah dibaca' in payload['feedback']
        assert 'tercakup' in payload['feedback']
        return _response(json.dumps({
            'commentary': 'Bukti cukup.',
            'report': {'title': 'Audit', 'executive_summary': 'x', 'methodology': 'y',
                       'findings': [], 'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=6, call=call)
    assert state['status'] == 'completed'
    assert len(state['observations']) == 1


def test_partially_new_read_range_is_allowed(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip_with('big.py', '\n'.join(
        f'line_{i} = {i}' for i in range(1, 301))), 'big.zip')
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Baca awal file.',
                'action': {'tool': 'read_source', 'arguments': {
                    'path': 'big.py', 'start_line': 1, 'limit': 100}}}))
        if calls['n'] == 2:
            return _response(json.dumps({
                'commentary': 'Lanjutkan ke baris baru.',
                'action': {'tool': 'read_source', 'arguments': {
                    'path': 'big.py', 'start_line': 50, 'limit': 100}}}))
        return _response(json.dumps({
            'commentary': 'Bukti cukup.',
            'report': {'title': 'Audit', 'executive_summary': 'x', 'methodology': 'y',
                       'findings': [], 'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=6, call=call)
    assert state['status'] == 'completed'
    assert len(state['observations']) == 2


def test_payload_keeps_content_excerpt_for_older_observations():
    content = 'A' * 4000
    observations = [{
        'id': f'obs-{index}', 'tool': 'read_source', 'target': 'app.py',
        'sha256': 'abc', 'data': {
            'start_line': index * 10 + 1, 'returned_lines': 10, 'content': content}}
        for index in range(7)]
    state = {'objective': 'Cari', 'observations': observations, 'max_iterations': 12,
             'iterations': 7, 'token_budget': 50000, 'tokens_used': 0,
             'notes': '', 'feedback': ''}
    payload = _message_payload(state, {
        'name': 'app.zip', 'excluded': 0,
        'files': {'app.py': {'lines': 70, 'sha256': 'abc'}}})

    assert len(payload['observations']) == 7
    older = payload['observations'][0]['data']
    assert older['content_excerpt'] is True
    assert older['truncated'] is True
    assert 'karakter tengah tidak ditampilkan' in older['content']
    assert len(older['content']) < len(content)
    recent = payload['observations'][-1]['data']
    assert recent['content'] == content
    assert 'content_excerpt' not in recent


def test_low_iteration_budget_directs_model_to_report(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    seen = {}

    def call(**kwargs):
        payload = json.loads(kwargs['messages'][-1]['content'])
        seen['directive'] = payload.get('directive', '')
        return _response(json.dumps({
            'commentary': 'Laporan.',
            'report': {'title': 'Audit', 'executive_summary': 'x', 'methodology': 'y',
                       'findings': [], 'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=2, call=call)
    assert state['status'] == 'completed'
    assert 'JANGAN membaca file lagi' in seen['directive']


def test_invalid_model_output_is_logged_with_validator_detail(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')

    def call(**kwargs):
        return _response('{not valid json')

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=4, call=call)
    assert state['status'] == 'completed_with_errors'
    assert state['stop_reason'] == 'model_schema_failed'
    assert 'Error terakhir:' in state['error']
    errors = (run_dir / 'code-model-errors.ndjson').read_text(encoding='utf-8').splitlines()
    assert len(errors) == 3
    first = json.loads(errors[0])
    assert first['content'] == '{not valid json'
    assert 'error' in first


def test_first_json_object_wins_when_model_emits_two(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')
    calls = {'n': 0}

    def call(**kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            return _response(json.dumps({
                'commentary': 'Baca app.py.',
                'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}})
                + '\n\n' + json.dumps({
                    'commentary': 'Duplikat.',
                    'action': {'tool': 'read_source', 'arguments': {'path': 'app.py'}}}))
        return _response(json.dumps({
            'commentary': 'Laporan.',
            'report': {'title': 'Audit', 'executive_summary': 'x', 'methodology': 'y',
                       'findings': [], 'limitations': 'z', 'next_steps': 'z'}}))

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=4, call=call)
    assert state['status'] == 'completed'
    assert calls['n'] == 2
    assert len(state['observations']) == 1


def test_provider_content_refusal_is_not_reported_as_schema_failure(tmp_path):
    run_dir = tmp_path / 'run'
    bundle = write_bundle(run_dir, _zip(), 'app.zip')

    def call(**kwargs):
        return _response('[req_x] [glm-5.3]\n**Request rejected by AI provider (HTTP 400)**\n'
                         '- Most common cause: its CONTENT FILTER / safety moderation rejected the prompt.')

    state = run_audit(run_dir, 'Cari', model='fake/model', bundle=bundle,
                      token_budget=50000, max_iterations=3, call=call)
    assert state['stop_reason'] == 'provider_rejected'
    assert not (run_dir / 'code-model-errors.ndjson').exists()
