"""Read-only source namespaces for code audit.

Ported from ADAPTIX-V2's engine/sources.py, without Docker, a database, or the
vault: the sanitized bundle is a JSON file on disk (0600). Uploaded programs are
never extracted as files, installed, imported, or executed. Only UTF-8 text
inside the archive is read, redacted, and stored as data for the model.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import time
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE = 4_000_000
MAX_TOTAL = 8_000_000
MAX_FILE = 200_000
MAX_FILES = 300

EXTENSIONS = {
    '.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.php', '.go', '.java',
    '.rb', '.rs', '.cs', '.c', '.cpp', '.h', '.hpp', '.swift', '.kt', '.sql',
    '.yaml', '.yml', '.json', '.toml', '.ini', '.html', '.sh', '.md', '.txt',
    '.xml', '.vue', '.svelte',
}
PRIVATE = {'.git', '.env', '.ssh', 'node_modules', '__pycache__', '.venv', 'venv'}
_GENERATED_BACKUP = re.compile(r'^.+_backup_\d{8}-\d{6}(?:-\d+)?$')
_NAMED_SECRET = re.compile(
    r'''(?im)(\b(?:password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret|secret[_-]?key)\b\s*[:=]\s*)(["'])([^\r\n]*?)(\2)'''
)
_TOKEN_SECRET = re.compile(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}')


def redact(text: str) -> str:
    """Remove credential values while preserving line numbers and syntax."""
    text = _NAMED_SECRET.sub(lambda m: m[1] + m[2] + '[REDACTED]' + m[4], text)
    return _TOKEN_SECRET.sub('[REDACTED]', text)


def unpack(raw: bytes) -> dict:
    """Validate an uploaded ZIP and return sanitized text files.

    Every rejection is a ValueError the API can show to the operator. The archive
    is read in memory; nothing is written besides the resulting sanitized bundle.
    """
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_ARCHIVE:
        raise ValueError('ZIP maksimal 4 MB.')
    files: dict[str, dict] = {}
    total = 0
    excluded = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.infolist()) > 1000:
                raise ValueError('Arsip memiliki terlalu banyak entri.')
            for item in archive.infolist():
                name = item.filename
                if '\\' in name or '\x00' in name or any(ord(c) < 32 for c in name):
                    raise ValueError('Nama file arsip tidak valid.')
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or not path.parts or ':' in path.parts[0]:
                    raise ValueError('Path arsip berada di luar namespace.')
                mode = item.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise ValueError('Arsip tidak boleh memuat symlink atau file khusus.')
                if item.is_dir():
                    continue
                if (any(part in PRIVATE for part in path.parts)
                        or any(_GENERATED_BACKUP.match(part) for part in path.parts)
                        or path.name.startswith('.env')
                        or path.suffix.lower() not in EXTENSIONS):
                    excluded += 1
                    continue
                if name in files:
                    raise ValueError('Path file dalam ZIP berulang.')
                if len(files) >= MAX_FILES or item.file_size > MAX_FILE:
                    raise ValueError('Maksimal 300 file teks, masing-masing 200 KB.')
                with archive.open(item) as stream:
                    data = stream.read(MAX_FILE + 1)
                total += len(data)
                if len(data) > MAX_FILE or total > MAX_TOTAL:
                    raise ValueError('Ukuran source terurai maksimal 8 MB.')
                try:
                    text = data.decode('utf-8')
                except UnicodeError:
                    excluded += 1
                    continue
                if '\x00' in text:
                    excluded += 1
                    continue
                safe = redact(text)
                files[name] = {
                    'text': safe,
                    'sha256': hashlib.sha256(safe.encode()).hexdigest(),
                    'lines': len(safe.splitlines()),
                }
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError('ZIP tidak dapat dibaca atau terenkripsi.') from exc
    if not files:
        raise ValueError('ZIP tidak memiliki source teks yang dapat dianalisis.')
    return {'files': files, 'excluded': excluded, 'sha256': hashlib.sha256(raw).hexdigest()}


def _allowed_roots():
    raw = os.getenv('ADAPTIX_CODE_AUDIT_ROOTS', '')
    roots = []
    for part in raw.split(os.pathsep):
        part = part.strip()
        if not part:
            continue
        try:
            roots.append(Path(part).expanduser().resolve())
        except OSError:
            continue
    return roots


def directory_bundle(source_dir, *, name=None) -> dict:
    """Read a local source folder into the same sanitized bundle shape as a ZIP.

    The folder is read-only: nothing is written, imported, or executed. Entries
    that a ZIP would reject (symlinks, private directories, binaries) are skipped
    and counted, while the same per-file/total/count limits are enforced. Set
    ``ADAPTIX_CODE_AUDIT_ROOTS`` (os.pathsep-separated) to confine which folders
    the dashboard may read.
    """
    source = Path(source_dir).expanduser().resolve()
    if not source.is_dir():
        raise ValueError('Folder source tidak ditemukan atau bukan direktori.')
    roots = _allowed_roots()
    if roots and not any(source == root or root in source.parents for root in roots):
        raise ValueError('Folder source berada di luar ADAPTIX_CODE_AUDIT_ROOTS.')
    files: dict[str, dict] = {}
    total = 0
    excluded = 0
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        dirnames[:] = sorted(part for part in dirnames
                             if part not in PRIVATE and not _GENERATED_BACKUP.match(part))
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            relative = path.relative_to(source)
            if (any(part in PRIVATE for part in relative.parts)
                    or filename.startswith('.env') or path.is_symlink()
                    or not path.is_file()
                    or path.suffix.lower() not in EXTENSIONS):
                excluded += 1
                continue
            try:
                data = path.read_bytes()
            except OSError:
                excluded += 1
                continue
            if len(data) > MAX_FILE:
                raise ValueError('Maksimal 200 KB per file teks.')
            total += len(data)
            if total > MAX_TOTAL:
                raise ValueError('Ukuran source maksimal 8 MB.')
            try:
                text = data.decode('utf-8')
            except UnicodeError:
                excluded += 1
                continue
            if '\x00' in text:
                excluded += 1
                continue
            if len(files) >= MAX_FILES:
                raise ValueError('Maksimal 300 file teks.')
            safe = redact(text)
            files[relative.as_posix()] = {
                'text': safe,
                'sha256': hashlib.sha256(safe.encode()).hexdigest(),
                'lines': len(safe.splitlines()),
            }
    if not files:
        raise ValueError('Folder tidak memiliki source teks yang dapat dianalisis.')
    digest = hashlib.sha256()
    for rel_name in sorted(files):
        digest.update(rel_name.encode())
        digest.update(files[rel_name]['sha256'].encode())
    return {'files': files, 'excluded': excluded, 'sha256': digest.hexdigest(),
            'name': name or source.name, 'source_path': str(source)}


def _persist_bundle(run_dir: Path, bundle: dict, name: str, *, kind: str,
                    source_path: str = '') -> dict:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / 'code-bundle.json'
    payload = {
        'name': name,
        'source_kind': kind,
        'source_path': source_path,
        'sha256': bundle['sha256'],
        'files': bundle['files'],
        'excluded': bundle['excluded'],
        'created': time.time(),
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    bundle['source_kind'] = kind
    bundle['source_path'] = source_path
    return bundle


def write_bundle(run_dir: Path, raw: bytes, name: str) -> dict:
    """Sanitize an upload and persist only the sanitized bundle (never the ZIP)."""
    return _persist_bundle(run_dir, unpack(raw), name, kind='zip')


def write_directory_bundle(run_dir: Path, source_dir, *, name=None) -> dict:
    """Sanitize a local folder and persist only the text bundle."""
    source = Path(source_dir).expanduser().resolve()
    bundle = directory_bundle(source, name=name)
    return _persist_bundle(run_dir, bundle, bundle['name'], kind='folder',
                           source_path=str(source))


def load_bundle(run_dir: Path) -> dict:
    path = Path(run_dir) / 'code-bundle.json'
    if not path.is_file():
        raise FileNotFoundError(f'source bundle missing: {path}')
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)
