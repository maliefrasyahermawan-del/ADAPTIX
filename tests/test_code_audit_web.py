import io
import json
import zipfile

from src.adaptix.web import app as webapp


def _zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('app.py', 'print(1)\n')
    return buffer.getvalue()


def test_audit_models_offer_deepseek():
    client = webapp.create_app().test_client()
    data = client.get('/api/audit/models').get_json()
    assert 'deepseek/deepseek-chat' in data['models']
    assert data['default']


def test_upload_rejects_invalid_zip(monkeypatch):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    response = client.post('/api/audit/code', data={
        'file': (io.BytesIO(b'not a zip'), 'source.zip'),
        'instruction': 'Cari kerentanan',
    }, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'ZIP' in response.get_json()['error']


def test_upload_starts_code_engine(monkeypatch):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    calls = {}

    def fake_start(runner, instruction, archive, filename, model, budgets, *, source_limits=None):
        calls.update(instruction=instruction, filename=filename, model=model, budgets=budgets,
                     source_limits=source_limits)
        runner.view.engine = 'code'
        runner.view.run_id = 'code-fake'
        runner.view.status = 'starting'
        runner.view.target = [filename]
        runner.view.model = model
        runner.view.details = []
        return 'code-fake'

    monkeypatch.setattr(webapp, 'start_code', fake_start)
    response = client.post('/api/audit/code', data={
        'file': (io.BytesIO(_zip()), 'source.zip'),
        'instruction': 'Cari kebocoran kredensial',
        'model': 'deepseek/deepseek-chat',
        'time_budget': '120',
        'token_budget': '20000',
        'max_iterations': '4',
    }, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.get_json()['run_id'] == 'code-fake'
    assert calls['filename'] == 'source.zip'
    assert calls['budgets'] == {'time_budget': 120, 'token_budget': 20000, 'max_iterations': 4}


def test_code_snapshot_rebuilds_findings_and_terminals(tmp_path):
    run = tmp_path / 'code-test'
    run.mkdir()
    (run / 'logs').mkdir()
    (run / 'code-meta.json').write_text(json.dumps({
        'instruction': 'Audit source', 'source_name': 'app.zip', 'model': 'fake/model',
        'files': 1, 'excluded': 0,
        'budgets': {'max_iterations': 4}}), encoding='utf-8')
    (run / 'code-report.json').write_text(json.dumps({
        'status': 'completed', 'stop_reason': 'model_reported', 'llm_model': 'fake/model',
        'target': ['app.zip'], 'findings': [{
            'title': 'SQL injection', 'severity': 'high', 'cwe': 'CWE-89',
            'description': 'x', 'impact': 'y', 'remediation': 'z',
            'evidence': [{'target': 'app.py'}],
        }],
    }), encoding='utf-8')
    (run / 'logs' / 'worker.log').write_text('[tool] read_source app.py\n', encoding='utf-8')

    view = webapp._code_snapshot('code-test', str(run))
    assert view.engine == 'code'
    assert view.status == 'completed'
    assert view.details[0]['title'] == 'SQL injection'
    assert view.details[0]['class'] == 'code'
    assert view.external['source']['name'] == 'app.zip'


def test_folder_source_starts_code_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    source = tmp_path / 'project'
    source.mkdir()
    (source / 'app.py').write_text('print(1)\n', encoding='utf-8')
    calls = {}

    def fake_start(runner, instruction, archive, filename, model, budgets, *, source_path=None,
                   auto_patch=False, source_limits=None):
        calls.update(archive=archive, filename=filename, source_path=source_path,
                     auto_patch=auto_patch, instruction=instruction, budgets=budgets)
        runner.view.engine = 'code'
        runner.view.run_id = 'code-fake'
        runner.view.status = 'starting'
        runner.view.target = [str(source)]
        runner.view.model = model
        runner.view.details = []
        return 'code-fake'

    monkeypatch.setattr(webapp, 'start_code', fake_start)
    response = client.post('/api/audit/code', data={
        'source_path': str(source),
        'instruction': 'Audit folder',
        'model': 'deepseek/deepseek-chat',
    }, content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.get_json()['run_id'] == 'code-fake'
    assert calls['source_path'] == str(source)
    assert calls['archive'] is None
    assert calls['filename'] == 'project'


def test_requires_zip_or_folder(monkeypatch):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    response = client.post('/api/audit/code', data={
        'instruction': 'Audit',
    }, content_type='multipart/form-data')
    assert response.status_code == 400


def test_folder_auto_patch_flag_reaches_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    calls = {}

    def fake_start(runner, instruction, archive, filename, model, budgets, *, source_path=None,
                   auto_patch=False, source_limits=None):
        calls.update(source_path=source_path, auto_patch=auto_patch)
        runner.view.engine = 'code'
        runner.view.run_id = 'code-fake'
        runner.view.status = 'starting'
        runner.view.target = [str(source_path)]
        runner.view.model = model
        runner.view.details = []
        return 'code-fake'

    monkeypatch.setattr(webapp, 'start_code', fake_start)
    response = client.post('/api/audit/code', data={
        'source_path': str(tmp_path),
        'instruction': 'Audit folder',
        'auto_patch': '1',
    }, content_type='multipart/form-data')
    assert response.status_code == 200
    assert calls['auto_patch'] is True


def test_file_limit_choices_reach_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    calls = {}

    def fake_start(runner, instruction, archive, filename, model, budgets, *, source_path=None,
                   auto_patch=False, source_limits=None):
        calls.update(source_limits=source_limits)
        runner.view.engine = 'code'
        runner.view.run_id = 'code-fake'
        runner.view.status = 'starting'
        runner.view.target = [str(source_path)]
        runner.view.model = model
        runner.view.details = []
        return 'code-fake'

    monkeypatch.setattr(webapp, 'start_code', fake_start)
    response = client.post('/api/audit/code', data={
        'source_path': str(tmp_path),
        'instruction': 'Audit folder',
        'max_file_kb': '1024',
        'oversize': 'fail',
    }, content_type='multipart/form-data')
    assert response.status_code == 200
    assert calls['source_limits'] == {'max_file': 1_024_000, 'oversize': 'fail'}


def test_file_limit_defaults_and_clamps(monkeypatch, tmp_path):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    calls = {}

    def fake_start(runner, instruction, archive, filename, model, budgets, *, source_path=None,
                   auto_patch=False, source_limits=None):
        calls.update(source_limits=source_limits)
        runner.view.engine = 'code'
        runner.view.run_id = 'code-fake'
        runner.view.status = 'starting'
        runner.view.target = [str(source_path)]
        runner.view.model = model
        runner.view.details = []
        return 'code-fake'

    monkeypatch.setattr(webapp, 'start_code', fake_start)
    client.post('/api/audit/code', data={
        'source_path': str(tmp_path),
        'instruction': 'Audit folder',
        'max_file_kb': '9999',
        'oversize': 'bogus',
    }, content_type='multipart/form-data')
    assert calls['source_limits'] == {'max_file': 1024000, 'oversize': 'skip'}


def test_audit_preflight_warns_about_oversized_root(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    big = tmp_path / 'big.html'
    big.write_text('a' * 300_000, encoding='utf-8')
    (tmp_path / 'small.py').write_text('print(1)', encoding='utf-8')
    resp = client.get('/api/audit/preflight', query_string={
        'source_path': str(tmp_path), 'max_file_kb': '200'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(o['name'] == 'big.html' for o in data['oversized'])
    assert data['warnings']
    # at 1024 KB nothing warns
    resp2 = client.get('/api/audit/preflight', query_string={
        'source_path': str(tmp_path), 'max_file_kb': '1024'})
    assert resp2.get_json()['warnings'] == []


def test_excluded_files_reasons_available(tmp_path):
    from src.adaptix.code_audit.sources import directory_bundle
    src = tmp_path / 'project'
    src.mkdir()
    (src / 'app.py').write_text('print(1)', encoding='utf-8')
    (src / 'big.html').write_text('a' * 300_000, encoding='utf-8')
    bundle = directory_bundle(src, max_file=200_000, oversize='skip')
    assert bundle['excluded'] >= 1
    rows = bundle.get('excluded_files') or []
    assert any(r.get('path') == 'big.html' and r.get('reason') == 'oversize_skip' for r in rows)


def test_auto_patch_rejects_zip(monkeypatch):
    monkeypatch.setattr(webapp, 'runner', webapp.Runner(webapp._default_view()))
    client = webapp.create_app().test_client()
    response = client.post('/api/audit/code', data={
        'file': (io.BytesIO(_zip()), 'source.zip'),
        'instruction': 'Audit',
        'auto_patch': '1',
    }, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'folder lokal' in response.get_json()['error']
