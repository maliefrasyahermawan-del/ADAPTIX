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


def write_bundle(run_dir: Path, raw: bytes, name: str) -> dict:
    """Sanitize an upload and persist only the sanitized bundle (never the ZIP)."""
    bundle = unpack(raw)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / 'code-bundle.json'
    payload = {
        'name': name,
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
    return bundle


def load_bundle(run_dir: Path) -> dict:
    path = Path(run_dir) / 'code-bundle.json'
    if not path.is_file():
        raise FileNotFoundError(f'source bundle missing: {path}')
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)
