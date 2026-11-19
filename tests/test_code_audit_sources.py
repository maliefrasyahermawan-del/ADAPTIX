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
