"""Launch and supervise one static code-audit worker (no Docker)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from src.adaptix.code_audit.sources import write_bundle, write_directory_bundle
from src.adaptix.config import ROOT

ANSI = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')


def _run_dir(run_id):
    return ROOT / 'artifacts' / 'scans' / run_id


def _read_json(path):
    try:
        with Path(path).open(encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def details(record):
    rows = []
    for finding in record.get('findings') or []:
        evidence = finding.get('evidence') or []
        paths = ', '.join(str(row.get('target') or '') for row in evidence if row.get('target'))
        rows.append({
            'endpoint': paths,
            'parameter': '',
            'payload': '',
            'url': paths,
            'class': 'code',
            'severity': str(finding.get('severity') or 'info'),
            'status': 'model_assessed',
            'title': str(finding.get('title') or ''),
            'cwe': str(finding.get('cwe') or ''),
            'cause': str(finding.get('description') or '')[:600],
            'mitigation': str(finding.get('remediation') or '')[:600],
            'impact': str(finding.get('impact') or '')[:400],
            'extracted': [],
            'impact_proven': False,
        })
    return rows


def _apply_progress(view, run_dir):
    progress = _read_json(run_dir / 'code-progress.json')
    if not progress:
        return
    view.status = str(progress.get('status') or view.status)
    view.workflow_phase = str(progress.get('node') or view.workflow_phase)
    view.iteration = int(progress.get('iterations') or 0)
    view.max_iterations = int(progress.get('max_iterations') or view.max_iterations)
    view.stop_reason = str(progress.get('stop_reason') or '')
    external = dict(view.external or {})
    external['progress'] = progress
    view.external = external


def _apply_report(view, run_dir):
    report = _read_json(run_dir / 'code-report.json')
    if not report:
        return
    view.status = str(report.get('status') or view.status)
    view.stop_reason = str(report.get('stop_reason') or view.stop_reason)
    view.details = details(report)
    external = dict(view.external or {})
    external['report'] = report
    view.external = external


def start_code(runner, instruction, archive, filename, model, budgets, *, source_path=None,
               auto_patch=False, source_limits=None):
    """Validate the source (ZIP or local folder), persist its sanitized bundle, start the worker."""
    limits = dict(source_limits or {})
    run_id = time.strftime('code-%H%M%S')
    base = _run_dir(run_id)
    suffix = 1
    while base.exists():
        run_id = time.strftime('code-%H%M%S') + f'-{suffix}'
        base = _run_dir(run_id)
        suffix += 1
    base.mkdir(parents=True, exist_ok=True)
    try:
        if source_path:
            bundle = write_directory_bundle(base, source_path, **limits)
            source_kind = 'folder'
            display = bundle.get('source_path') or str(source_path)
            filename = bundle.get('name') or os.path.basename(str(source_path))
        else:
            bundle = write_bundle(base, archive, filename, **limits)
            source_kind = 'zip'
            display = filename
    except Exception:
        import shutil
        shutil.rmtree(base, ignore_errors=True)
        raise
    (base / 'logs').mkdir(exist_ok=True)

    request = {
        'engine': 'code', 'audit_kind': 'code', 'source_kind': source_kind,
        'source_name': filename, 'source_path': str(bundle.get('source_path') or ''),
        'source_sha256': bundle['sha256'], 'files': len(bundle['files']),
        'excluded': bundle['excluded'],
        'excluded_files': bundle.get('excluded_files', []),
        'instruction': instruction,
        'model': model, 'budgets': budgets, 'source_limits': limits,
        'auto_patch': bool(auto_patch), 'created': time.time(),
    }
    (base / 'code-meta.json').write_text(json.dumps(request, indent=2), encoding='utf-8')
    (base / 'code-request.json').write_text(
        json.dumps({**request, 'source_files': sorted(bundle['files'])}, indent=2), encoding='utf-8')

    view = runner.view
    runner.run_id = run_id
    runner.engine = 'code'
    view.run_id = run_id
    view.engine = 'code'
    view.objective = instruction
    view.target = [display]
    view.model = model
    view.status = 'starting'
    view.stop_reason = ''
    view.log = []
    view.details = []
    view.started_at = time.time()
    view.workflow_node = 'code_audit'
    view.workflow_phase = 'starting'
    view.iteration = 0
    view.max_iterations = int(budgets.get('max_iterations') or 8)
    view.external = {'engine': 'code-audit', 'source': {
        'name': filename, 'kind': source_kind,
        'path': bundle.get('source_path') or '',
        'sha256': bundle['sha256'], 'files': len(bundle['files']),
        'excluded': bundle['excluded'], 'limits': limits}, 'activity': []}
    view.append(f'source: {display} - {source_kind} ({len(bundle["files"])} file teks, '
                f'{bundle["excluded"]} dikecualikan)')
    if limits:
        view.append('batas file: {} KB, file besar: {}'.format(
            int(limits.get('max_file') or 200_000) // 1000,
            'dilewati' if limits.get('oversize') == 'skip' else 'gagalkan audit'))
    if auto_patch:
        view.append('auto-patch: aktif (tulis ke folder sumber setelah laporan, dengan backup)')
    view.append(f'objective: {instruction[:160]}')

    interpreter = runner.interpreter()
    argv = [interpreter, '-u', '-m', 'src.adaptix.code_audit.worker',
            '--run-dir', str(base), '--instruction', instruction, '--model', model,
            '--time-budget', str(int(budgets.get('time_budget') or 900)),
            '--token-budget', str(int(budgets.get('token_budget') or 50000)),
            '--max-iterations', str(int(budgets.get('max_iterations') or 8))]
    if auto_patch:
        argv.append('--auto-patch')
    from src.adaptix import provider_keys
    env = provider_keys.env_for_model(model, dict(os.environ, PYTHONUNBUFFERED='1'))
    runner.process = subprocess.Popen(argv, cwd=str(ROOT), env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1)
    runner.finished.clear()
    log_path = base / 'logs' / 'worker.log'

    def work():
        try:
            with log_path.open('a', encoding='utf-8') as log:
                for raw in runner.process.stdout or []:
                    line = ANSI.sub('', raw).rstrip()
                    if not line:
                        continue
                    log.write(line + '\n')
                    log.flush()
                    view.append(line[:1200])
            code = runner.process.wait()
            _apply_progress(view, base)
            _apply_report(view, base)
            if not view.external.get('report'):
                progress = view.external.get('progress') or {}
                view.status = progress.get('status') or ('completed' if code == 0 else 'completed_with_errors')
                view.stop_reason = progress.get('stop_reason') or 'external_exit'
            view.workflow_phase = 'completed'
            view.append(f'audit finished (exit {code})')
        except Exception as exc:
            view.append(f'code audit runner error: {type(exc).__name__}: {exc}'[:500])
            view.status = 'completed_with_errors'
            view.stop_reason = 'runner_error'
        finally:
            runner.finished.set()

    def poller():
        while runner.process.poll() is None:
            _apply_progress(view, base)
            _apply_report(view, base)
            activity = []
            try:
                with (base / 'code-activity.ndjson').open(encoding='utf-8') as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            activity.append(json.loads(line))
                        except ValueError:
                            continue
            except OSError:
                pass
            if activity:
                external = dict(view.external or {})
                external['activity'] = activity[-200:]
                view.external = external
            if view.status == 'starting':
                view.status = 'running'
            if view.started_at:
                view.elapsed = time.time() - view.started_at
            time.sleep(1.0)

    runner.thread = threading.Thread(target=work, daemon=True)
    runner.thread.start()
    threading.Thread(target=poller, daemon=True).start()
    return run_id


def kill_code(runner):
    proc = getattr(runner, 'process', None)
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    except OSError:
        pass
