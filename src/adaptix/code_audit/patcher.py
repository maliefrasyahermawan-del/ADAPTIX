"""Apply model-proposed exact patches to an audited local folder.

This is the only module that writes to the operator's source tree. It is opt-in
per run, works only on files that were part of the audited bundle, requires an
exact and unique ``search`` snippet, and reports skips instead of guessing.
Paths are resolved under the audited root and symlinks are refused, so a hostile
report cannot escape the folder it names.

Before the first byte is written, the audited folder itself is copied beside it
in its parent directory as ``<folder>_backup_<timestamp>``. A failed backup aborts
every write.
"""
from __future__ import annotations

import difflib
import json
import os
import shutil
import time
from pathlib import Path

MAX_PATCHES = 20
MAX_PATCH_BYTES = 200_000
SNIPPET_PREVIEW_CHARS = 4000


def _preview(text):
    if len(text) <= SNIPPET_PREVIEW_CHARS:
        return text, False
    return text[:SNIPPET_PREVIEW_CHARS], True


def _under(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _write_atomic(path: Path, text: str) -> None:
    mode = path.stat().st_mode
    temp = path.with_name('.' + path.name + '.adaptix-patch.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        try:
            if temp.exists():
                temp.unlink()
        except OSError:
            pass


def project_backup_path(source_root: Path) -> tuple[Path | None, str | None]:
    """Return the folder where the audited folder is backed up before patching.

    The backup is a sibling of the audited folder, so auditing
    ``/.../Web/[MEDIUM] plunder`` stores the whole ``[MEDIUM] plunder`` tree at
    ``/.../Web/[MEDIUM] plunder_backup_<timestamp>``. Filesystem roots and the
    operator's home directory are refused because copying those is not a project
    backup.
    """
    source_root = Path(source_root).resolve()
    parent = source_root.parent
    if parent == source_root:
        return None, 'Folder audit adalah filesystem root; backup ditolak.'
    try:
        if source_root == Path.home().resolve():
            return None, 'Folder audit adalah home directory; backup ditolak.'
    except OSError:
        pass
    stamp = time.strftime('%Y%m%d-%H%M%S')
    base = f'{source_root.name}_backup_{stamp}'
    candidate = parent / base
    suffix = 1
    while candidate.exists():
        candidate = parent / f'{base}-{suffix}'
        suffix += 1
    return candidate, None


def _backup_project(source_root: Path) -> tuple[Path | None, str | None]:
    destination, error = project_backup_path(source_root)
    if destination is None:
        return None, error
    try:
        shutil.copytree(Path(source_root).resolve(), destination, symlinks=True)
    except (OSError, shutil.Error) as exc:
        return None, f'{type(exc).__name__}: {exc}'
    return destination, None


def apply_patches(source_root, patches, *, run_dir=None, files=None) -> dict:
    """Apply exact search/replace patches to ``source_root``.

    ``files`` is the audited bundle catalog; a patch for any other path is
    skipped. The audited folder is backed up once beside itself, before the first
    write, when at least one patch is ready to apply. Returns a JSON-serializable
    outcome.
    """
    root = Path(source_root).expanduser().resolve()
    outcome = {
        'enabled': True,
        'root': str(root),
        'backup_root': '',
        'applied': [],
        'skipped': [],
        'started_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    if not root.is_dir():
        outcome['error'] = 'Folder source tidak ditemukan.'
        return outcome
    allowed = set(files or [])
    pending = []
    for proposal in (patches or [])[:MAX_PATCHES]:
        rel = str(proposal.get('path') or '')
        row = {'path': rel, 'status': 'skipped', 'reason': ''}
        if rel not in allowed:
            row['reason'] = 'Path tidak ada di katalog audit.'
            outcome['skipped'].append(row)
            continue
        target = (root / rel).resolve()
        if not _under(root, target):
            row['reason'] = 'Path keluar dari folder audit.'
            outcome['skipped'].append(row)
            continue
        if target.is_symlink() or not target.is_file():
            row['reason'] = 'Bukan file reguler (symlink ditolak).'
            outcome['skipped'].append(row)
            continue
        search = proposal.get('search') or ''
        replace = proposal.get('replace') or ''
        if not isinstance(search, str) or not isinstance(replace, str) or not search:
            row['reason'] = 'Snippet search kosong atau bukan teks.'
            outcome['skipped'].append(row)
            continue
        if len(search.encode()) > MAX_PATCH_BYTES or len(replace.encode()) > MAX_PATCH_BYTES:
            row['reason'] = 'Patch terlalu besar.'
            outcome['skipped'].append(row)
            continue
        try:
            original = target.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            row['reason'] = f'File tidak terbaca: {type(exc).__name__}'
            outcome['skipped'].append(row)
            continue
        count = original.count(search)
        if count != 1:
            row['reason'] = f'Snippet search muncul {count} kali; harus tepat 1.'
            outcome['skipped'].append(row)
            continue
        if search == replace:
            row['reason'] = 'Patch tidak mengubah apa pun.'
            outcome['skipped'].append(row)
            continue
        index = original.find(search)
        line = original.count('\n', 0, index) + 1
        pending.append({
            'rel': rel, 'target': target, 'original': original,
            'updated': original.replace(search, replace, 1), 'row': row,
            'line': line, 'line_end': line + search.count('\n'),
            'before': search, 'after': replace,
            'rationale': str(proposal.get('rationale') or '')[:1000],
        })

    if pending:
        backup, error = _backup_project(root)
        if backup is None:
            for item in pending:
                item['row']['reason'] = f'Backup folder gagal; tidak ada file diubah: {error}'
                outcome['skipped'].append(item['row'])
            pending = []
            outcome['backup_error'] = error or 'Backup folder gagal.'
        else:
            outcome['backup_root'] = str(backup)

    diffs = []
    for item in pending:
        rel, target, row = item['rel'], item['target'], item['row']
        try:
            if run_dir is not None:
                backup = (Path(run_dir) / 'patches' / 'backup' / rel).resolve()
                if not _under(Path(run_dir).resolve(), backup):
                    raise ValueError('backup escape')
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            _write_atomic(target, item['updated'])
        except (OSError, ValueError) as exc:
            row['reason'] = f'Gagal menulis: {type(exc).__name__}: {exc}'
            outcome['skipped'].append(row)
            continue
        row['status'] = 'applied'
        row['rationale'] = item['rationale']
        row['line'] = item['line']
        row['line_end'] = item['line_end']
        row['before'], row['before_truncated'] = _preview(item['before'])
        row['after'], row['after_truncated'] = _preview(item['after'])
        outcome['applied'].append(row)
        diffs.append(''.join(difflib.unified_diff(
            item['original'].splitlines(keepends=True),
            item['updated'].splitlines(keepends=True),
            fromfile=f'a/{rel}', tofile=f'b/{rel}')))

    outcome['applied_count'] = len(outcome['applied'])
    outcome['skipped_count'] = len(outcome['skipped'])
    outcome['finished_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if run_dir is not None:
        try:
            base = Path(run_dir)
            (base / 'patches').mkdir(parents=True, exist_ok=True)
            (base / 'patches' / 'adaptix.patch').write_text('\n'.join(diffs), encoding='utf-8')
            (base / 'patches' / 'results.json').write_text(
                json.dumps(outcome, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError:
            pass
    return outcome
