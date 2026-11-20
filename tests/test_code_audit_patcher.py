import json
from pathlib import Path

from src.adaptix.code_audit.patcher import apply_patches


def _project(tmp_path):
    source = tmp_path / 'project' / 'dist'
    source.mkdir(parents=True)
    (source / 'app.py').write_text(
        "def lookup(name):\n    return db.execute(\"SELECT * FROM users WHERE name = '%s'\" % name)\n",
        encoding='utf-8')
    return source


def test_applies_unique_patch_and_keeps_a_backup(tmp_path):
    source = _project(tmp_path)
    run = tmp_path / 'run'
    outcome = apply_patches(source, [{
        'path': 'app.py',
        'search': 'return db.execute("SELECT * FROM users WHERE name = \'%s\'" % name)',
        'replace': 'return db.execute("SELECT * FROM users WHERE name = ?", (name,))',
        'rationale': 'Parameterized query.',
    }], run_dir=run, files=['app.py'])
    assert outcome['applied_count'] == 1
    assert 'WHERE name = ?' in (source / 'app.py').read_text(encoding='utf-8')
    assert (run / 'patches' / 'backup' / 'app.py').is_file()
    assert (run / 'patches' / 'adaptix.patch').is_file()
    saved = json.loads((run / 'patches' / 'results.json').read_text(encoding='utf-8'))
    assert saved['applied'][0]['path'] == 'app.py'
    applied = saved['applied'][0]
    assert applied['line'] == 2
    assert applied['line_end'] == 2
    assert "name = '%s'" in applied['before']
    assert 'name = ?' in applied['after']
    backup = Path(outcome['backup_root'])
    assert backup.parent == tmp_path / 'project'
    assert backup.name.startswith('dist_backup_')
    original = (backup / 'app.py').read_text(encoding='utf-8')
    assert "name = '%s'" in original


def test_skips_non_unique_missing_and_outside_paths(tmp_path):
    source = _project(tmp_path)
    (source / 'other.py').write_text('x = 1\nx = 1\n', encoding='utf-8')
    outcome = apply_patches(source, [
        {'path': 'other.py', 'search': 'x = 1', 'replace': 'x = 2', 'rationale': 'r'},
        {'path': 'missing.py', 'search': 'x', 'replace': 'y', 'rationale': 'r'},
        {'path': '../escape.py', 'search': 'x', 'replace': 'y', 'rationale': 'r'},
    ], files=['app.py', 'other.py'])
    assert outcome['applied_count'] == 0
    assert outcome['skipped_count'] == 3
    assert outcome['backup_root'] == ''
    assert 'x = 1\nx = 1\n' == (source / 'other.py').read_text(encoding='utf-8')


def test_refuses_symlinked_target(tmp_path):
    source = _project(tmp_path)
    outside = tmp_path / 'outside.py'
    outside.write_text('secret = 1\n', encoding='utf-8')
    (source / 'link.py').symlink_to(outside)
    outcome = apply_patches(source, [{
        'path': 'link.py', 'search': 'secret = 1', 'replace': 'secret = 2', 'rationale': 'r',
    }], files=['link.py'])
    assert outcome['applied_count'] == 0
    assert outside.read_text(encoding='utf-8') == 'secret = 1\n'


def test_failed_backup_aborts_every_write(tmp_path, monkeypatch):
    import shutil
    source = _project(tmp_path)

    def fail(*args, **kwargs):
        raise OSError('disk full')

    monkeypatch.setattr(shutil, 'copytree', fail)
    outcome = apply_patches(source, [{
        'path': 'app.py',
        'search': 'return db.execute("SELECT * FROM users WHERE name = \'%s\'" % name)',
        'replace': 'return db.execute("SELECT * FROM users WHERE name = ?", (name,))',
        'rationale': 'r',
    }], files=['app.py'])
    assert outcome['applied_count'] == 0
    assert outcome['backup_error']
    assert "name = '%s'" in (source / 'app.py').read_text(encoding='utf-8')


def test_refuses_home_or_filesystem_root_as_project(tmp_path):
    from src.adaptix.code_audit.patcher import project_backup_path
    assert project_backup_path(Path.home())[0] is None
    assert project_backup_path(Path('/'))[0] is None


def test_auditing_project_folder_backs_it_up_beside_itself(tmp_path):
    project = tmp_path / 'Web' / '[MEDIUM] plunder'
    (project / 'dist').mkdir(parents=True)
    (project / 'dist' / 'app.py').write_text('print(1)\n', encoding='utf-8')
    outcome = apply_patches(project, [{
        'path': 'dist/app.py', 'search': 'print(1)', 'replace': 'print(2)', 'rationale': 'r',
    }], files=['dist/app.py'])
    backup = Path(outcome['backup_root'])
    assert backup.parent == tmp_path / 'Web'
    assert backup.name.startswith('[MEDIUM] plunder_backup_')
    assert (backup / 'dist' / 'app.py').read_text(encoding='utf-8') == 'print(1)\n'
    assert (project / 'dist' / 'app.py').read_text(encoding='utf-8') == 'print(2)\n'
