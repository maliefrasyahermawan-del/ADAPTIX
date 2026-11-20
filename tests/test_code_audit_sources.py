import io
import stat
import zipfile

import pytest

from src.adaptix.code_audit.sources import unpack


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_accepts_text_sources_and_redacts_secrets():
    raw = _zip({'app.py': "API_KEY = 'sk-abcdefghijklmnopqrstuvwxyz123456'\nprint(1)\n",
                'README.md': 'hello'})
    bundle = unpack(raw)
    assert set(bundle['files']) == {'app.py', 'README.md'}
    assert 'sk-abcdefghijklmnopqrstuvwxyz123456' not in bundle['files']['app.py']['text']
    assert '[REDACTED]' in bundle['files']['app.py']['text']
    assert bundle['files']['app.py']['lines'] == 2


def test_excludes_private_dirs_and_binary_files():
    raw = _zip({'app.py': 'print(1)', '.env': 'SECRET=1',
                'node_modules/x.js': 'x', 'logo.png': b'\x89PNG'})
    bundle = unpack(raw)
    assert set(bundle['files']) == {'app.py'}
    assert bundle['excluded'] == 3


@pytest.mark.parametrize('name', ['../evil.py', '/etc/passwd.py', 'C:/evil.py'])
def test_rejects_namespace_escape(name):
    with pytest.raises(ValueError):
        unpack(_zip({name: 'print(1)'}))


def test_rejects_symlink_entries():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        info = zipfile.ZipInfo('link.py')
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, 'target.py')
    with pytest.raises(ValueError):
        unpack(buffer.getvalue())


def test_rejects_oversized_file():
    with pytest.raises(ValueError):
        unpack(_zip({'big.py': 'a' * 200_001}))


def test_rejects_archive_without_text_source():
    with pytest.raises(ValueError):
        unpack(_zip({'image.png': b'\x89PNG'}))


def test_directory_bundle_reads_text_and_skips_private_entries(tmp_path):
    from src.adaptix.code_audit.sources import directory_bundle
    source = tmp_path / 'project'
    (source / 'pkg').mkdir(parents=True)
    (source / 'pkg' / 'app.py').write_text(
        "API_KEY = 'sk-abcdefghijklmnopqrstuvwxyz123456'\nprint(1)\n", encoding='utf-8')
    (source / 'README.md').write_text('hello', encoding='utf-8')
    (source / '.env').write_text('SECRET=1', encoding='utf-8')
    (source / 'node_modules').mkdir()
    (source / 'node_modules' / 'x.js').write_text('x', encoding='utf-8')
    (source / 'logo.png').write_bytes(b'\x89PNG')
    bundle = directory_bundle(source)
    assert set(bundle['files']) == {'pkg/app.py', 'README.md'}
    assert bundle['name'] == 'project'
    assert bundle['excluded'] == 2
    assert 'sk-abcdefghijklmnopqrstuvwxyz123456' not in bundle['files']['pkg/app.py']['text']
    assert '[REDACTED]' in bundle['files']['pkg/app.py']['text']


def test_directory_bundle_rejects_missing_folder(tmp_path):
    from src.adaptix.code_audit.sources import directory_bundle
    with pytest.raises(ValueError):
        directory_bundle(tmp_path / 'missing')


def test_directory_bundle_honours_allowed_roots(tmp_path, monkeypatch):
    from src.adaptix.code_audit.sources import directory_bundle
    allowed = tmp_path / 'allowed'
    outside = tmp_path / 'outside'
    (allowed / 'src').mkdir(parents=True)
    (allowed / 'src' / 'app.py').write_text('print(1)', encoding='utf-8')
    outside.mkdir()
    (outside / 'app.py').write_text('print(1)', encoding='utf-8')
    monkeypatch.setenv('ADAPTIX_CODE_AUDIT_ROOTS', str(allowed))
    assert 'src/app.py' in directory_bundle(allowed)['files']
    with pytest.raises(ValueError):
        directory_bundle(outside)


def test_directory_bundle_skips_symlinks(tmp_path):
    from src.adaptix.code_audit.sources import directory_bundle
    source = tmp_path / 'project'
    source.mkdir()
    (source / 'app.py').write_text('print(1)', encoding='utf-8')
    (source / 'link.py').symlink_to(source / 'app.py')
    assert set(directory_bundle(source)['files']) == {'app.py'}


def test_directory_bundle_skips_adaptix_backup_folders(tmp_path):
    from src.adaptix.code_audit.sources import directory_bundle
    source = tmp_path / 'project'
    source.mkdir()
    (source / 'app.py').write_text('print(1)', encoding='utf-8')
    backup = source / 'project_backup_20261120-115547'
    backup.mkdir()
    (backup / 'app.py').write_text('print(0)', encoding='utf-8')
    assert set(directory_bundle(source)['files']) == {'app.py'}
