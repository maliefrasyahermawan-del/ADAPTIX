import os

from src.adaptix.web import app as webapp


def test_run_ids_are_ordered_by_creation_not_name(monkeypatch, tmp_path):
    scans = tmp_path / 'artifacts' / 'scans'
    scans.mkdir(parents=True)
    for name in ('code-140035', 'code-105202', 'code-105013'):
        (scans / name).mkdir()
    created = {'code-140035': 100, 'code-105202': 300, 'code-105013': 200}
    monkeypatch.setattr(webapp, 'CWD', str(tmp_path))
    monkeypatch.setattr(webapp.os.path, 'getctime',
                        lambda path: created[os.path.basename(path)])

    assert webapp._run_ids() == ['code-105202', 'code-105013', 'code-140035']
