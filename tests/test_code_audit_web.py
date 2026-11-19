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

    def fake_start(runner, instruction, archive, filename, model, budgets):
        calls.update(instruction=instruction, filename=filename, model=model, budgets=budgets)
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
