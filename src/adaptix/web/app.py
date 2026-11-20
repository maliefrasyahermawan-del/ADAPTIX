"""ADAPTIX web UI: a PentAGI-style dashboard served locally with Flask.

Reuses the exact same run controller as the curses TUI (``ui.runner.Runner``), so
this is a second skin on the same engine, never a second implementation. One run
at a time, same as the TUI and the CLI it wraps.
"""
from __future__ import annotations

import glob
import datetime
import json
import os
import re
import secrets
import subprocess
import time
from urllib.parse import urlsplit

from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from src.adaptix.code_audit.runner import details as code_details
from src.adaptix.code_audit.runner import start_code
from src.adaptix.config import ROOT, load_dotenv
from src.adaptix.opencode_runner import (DEFAULT_OPENCODE_MODEL, TERMINALS, opencode_models,
                                          peek_opencode_models)
from src.adaptix.ui.runner import Runner, configured_model, env_budget, resumable_runs
from src.adaptix.ui.state import LiveView, view_from_report, view_from_state

load_dotenv()

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
CWD = os.getcwd()


def _default_view() -> LiveView:
    view = LiveView()
    view.model = configured_model()
    view.context_tokens = int(os.getenv('ADAPTIX_MODEL_CONTEXT_TOKENS') or 32768)
    view.time_budget = env_budget('ADAPTIX_TIME_BUDGET', 2400)
    view.tool_budget = env_budget('ADAPTIX_TOOL_CALL_BUDGET', 90)
    view.token_budget = env_budget('ADAPTIX_TOKEN_BUDGET', 5000000)
    view.max_iterations = int(os.getenv('ADAPTIX_MAX_ITERATIONS') or 40)
    return view


runner = Runner(_default_view())


def _token_json(meter):
    return {
        'calls': meter.calls, 'provider_calls': meter.provider_calls,
        'cache_hits': meter.cache_hits, 'failed_calls': meter.failed_calls,
        'prompt_tokens': meter.prompt_tokens, 'completion_tokens': meter.completion_tokens,
        'charged': meter.charged, 'total': meter.total, 'budget': meter.budget,
        'remaining': meter.remaining, 'used_fraction': meter.used_fraction,
        'summary': meter.summary(),
    }


def _run_dir(run_id):
    return os.path.join(CWD, 'artifacts', 'scans', run_id)


_PRICE_TABLE = None


def _price_table():
    """litellm's bundled model price table, read as JSON so this dashboard does
    not import litellm just to price rows. Missing/corrupt table is treated as
    "prices unknown", which the UI renders as ``-``."""
    global _PRICE_TABLE
    if _PRICE_TABLE is None:
        _PRICE_TABLE = {}
        try:
            import litellm
            path = os.path.join(os.path.dirname(litellm.__file__),
                                'model_prices_and_context_window_backup.json')
            with open(path, encoding='utf-8') as handle:
                table = json.load(handle)
            if isinstance(table, dict):
                _PRICE_TABLE = table
        except Exception:
            _PRICE_TABLE = {}
    return _PRICE_TABLE


def _model_prices(model):
    table = _price_table()
    name = str(model or '')
    for key in (name, name.split('/')[-1]):
        row = table.get(key) if key else None
        if isinstance(row, dict) and row.get('input_cost_per_token') is not None:
            return row
    return {}


def _aggregate_usage(rows, key):
    groups = {}
    for row in rows:
        name = str(row.get(key) or 'unknown')
        group = groups.setdefault(name, {'name': name, 'calls': 0, 'tokens_in': 0, 'tokens_out': 0,
                                         'cache_in': 0, 'cache_out': 0, 'cost_in': 0.0,
                                         'cost_out': 0.0, 'cost_known': True})
        group['calls'] += 1
        group['tokens_in'] += row['prompt_tokens']
        group['tokens_out'] += row['completion_tokens']
        group['cache_in'] += row['cache_in']
        group['cache_out'] += row['cache_out']
        if row['total_cost'] is None:
            group['cost_known'] = False
        else:
            group['cost_in'] += row['cost_in']
            group['cost_out'] += row['cost_out']
    return sorted(groups.values(), key=lambda g: g['tokens_in'] + g['tokens_out'], reverse=True)


def _tool_call_rows(run_ids):
    """Per-function tool call counts and the durations that were actually
    recorded: ADAPTIX native runs record counts only (``execution_metrics``),
    opencode runs record a duration per activity row. A function with no
    recorded durations is returned with ``duration_known: false``."""
    groups = {}
    for run_id in run_ids:
        base = _run_dir(run_id)
        state = _checkpoint_state(base)
        metrics = state.get('execution_metrics') or {}
        for tool, count in (metrics.get('by_tool') or {}).items():
            group = groups.setdefault(str(tool), {'name': str(tool), 'type': 'Tool', 'count': 0,
                                                   'total_ms': 0, 'duration_known': False})
            group['count'] += int(count or 0)
        activity = os.path.join(base, 'external', 'pentest', 'activity.ndjson')
        if not os.path.isfile(activity):
            continue
        try:
            with open(activity, encoding='utf-8', errors='replace') as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    tool = str(row.get('tool') or row.get('agent') or '').strip()
                    if not tool:
                        continue
                    group = groups.setdefault(tool, {'name': tool,
                                                     'type': 'Agent' if not row.get('tool') else 'Tool',
                                                     'count': 0, 'total_ms': 0,
                                                     'duration_known': False})
                    group['count'] += 1
                    if row.get('duration_ms') is not None:
                        group['total_ms'] += int(row.get('duration_ms') or 0)
                        group['duration_known'] = True
        except OSError:
            continue
    return sorted(groups.values(), key=lambda g: g['count'], reverse=True)


def _run_seconds(base, state):
    external = state.get('external_engine') or {}
    try:
        elapsed = float(external.get('elapsed_seconds') or 0)
    except (TypeError, ValueError):
        elapsed = 0.0
    if elapsed > 0:
        return elapsed
    try:
        created = os.path.getctime(base)
        stamps = [os.path.getmtime(path) for path in glob.glob(os.path.join(base, '*.json'))]
    except OSError:
        return 0.0
    return max(0.0, max(stamps) - created) if stamps else 0.0


def _checkpoint_state(base):
    """The newest saved state for one run directory: its checkpoint, or its
    final report once the checkpoint is gone. Read once, reused by every
    per-flow tab instead of re-parsing the same file for each one."""
    checkpoints = sorted(glob.glob(os.path.join(base, 'checkpoint-*.json')), key=os.path.getmtime)
    if checkpoints:
        try:
            with open(checkpoints[-1], encoding='utf-8') as handle:
                return json.load(handle)
        except (OSError, ValueError):
            pass
    return Runner._latest_json(base, 'report-*.json') or {}


def _ledger_from_state(state):
    """Raw per-call token_ledger rows, enriched with provider, agent purpose and
    cost. Cost comes from litellm's bundled price table (the same table the
    provider integration uses), never from a hard-coded guess; a model with no
    table entry reports ``None`` and the dashboard shows ``-`` instead of $0."""
    rows = [r for r in (state.get('token_ledger') or []) if isinstance(r, dict)]
    out = []
    for row in rows:
        model = str(row.get('model') or 'unknown')
        prompt = int(row.get('prompt_tokens') or 0)
        completion = int(row.get('completion_tokens') or 0)
        failed = row.get('result') in ('failed', 'reasoning_starvation') or bool(row.get('error_type'))
        prices = _model_prices(model)
        cost_in = cost_out = None
        if prices and not failed:
            cost_in = prompt * float(prices.get('input_cost_per_token') or 0)
            cost_out = completion * float(prices.get('output_cost_per_token') or 0)
        out.append({'model': model,
                    'provider': model.split('/', 1)[0] if '/' in model else model,
                    'agent': str(row.get('purpose') or 'planner'),
                    'prompt_tokens': prompt,
                    'completion_tokens': completion,
                    'charged': int(row.get('tokens_charged') or 0),
                    'cache_in': int(row.get('cache_read_input_tokens') or 0),
                    'cache_out': int(row.get('cache_creation_input_tokens') or 0),
                    'cost_in': cost_in,
                    'cost_out': cost_out,
                    'total_cost': None if cost_in is None else cost_in + cost_out,
                    'cache_hit': row.get('source') == 'cache',
                    'failed': failed})
    return out


def _hypotheses_from_state(state):
    """Vulnerability categories the planner decided to investigate and why —
    ADAPTIX's real equivalent of a task checklist (it plans one adaptive
    hypothesis at a time, not a fixed named-subtask breakdown)."""
    rows = [r for r in (state.get('hypotheses') or []) if isinstance(r, dict)]
    return [{'category': str(r.get('category') or ''), 'target': str(r.get('target') or ''),
             'rationale': str(r.get('rationale') or '')} for r in rows]


def _screenshots_from_state(state, run_id):
    """Playwright evidence pages that have a saved screenshot, newest first."""
    rows = [r for r in (state.get('browser_evidence') or []) if isinstance(r, dict) and r.get('screenshot')]
    out = []
    for r in rows:
        name = os.path.basename(str(r['screenshot']))
        if os.path.isfile(os.path.join(_run_dir(run_id), name)):
            out.append({'file': name, 'url': str(r.get('url') or ''), 'title': str(r.get('title') or '')})
    return out


def _searches_from_state(state):
    """Pages ADAPTIX's browser tool actually visited during recon — the closest
    real equivalent to a "search log" ADAPTIX has; it has no web-search tool."""
    rows = [r for r in (state.get('browser_evidence') or []) if isinstance(r, dict)]
    return [{'url': str(r.get('url') or ''), 'title': str(r.get('title') or ''),
             'api_endpoints': len(r.get('api_endpoints') or []), 'links': len(r.get('links') or [])}
            for r in rows]


# Real, persisted data for the Templates/Resources/Knowledges pages — plain
# JSON lists and a plain upload folder, not a database, but genuinely saved
# to disk and genuinely usable, not a mock.
WEB_DATA_DIR = os.path.join(CWD, 'work', 'web_data')
RESOURCES_DIR = os.path.join(WEB_DATA_DIR, 'resources')


def _store_path(name):
    return os.path.join(WEB_DATA_DIR, f'{name}.json')


def _load_store(name):
    try:
        with open(_store_path(name), encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return []


def _save_store(name, items):
    os.makedirs(WEB_DATA_DIR, exist_ok=True)
    with open(_store_path(name), 'w', encoding='utf-8') as handle:
        json.dump(items, handle, indent=2)


def _settings_json():
    """The local operator profile behind the Settings screen.

    This is a real record saved in ``work/web_data/settings.json``, but it is a
    display profile, not authentication: ADAPTIX runs as one local operator and
    has no sign-in, so there is no password to store or check.
    """
    data = _load_store('settings')
    if not isinstance(data, dict):
        data = {}
    changed = False
    if not str(data.get('created_at') or '').strip():
        data['created_at'] = datetime.date.today().isoformat()
        changed = True
    if not str(data.get('display_name') or '').strip():
        data['display_name'] = 'admin'
        changed = True
    if not str(data.get('email') or '').strip():
        data['email'] = 'admin@adaptix.local'
        changed = True
    if changed:
        _save_store('settings', data)
    return data


def _git(args):
    try:
        out = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


_VERSION_INFO = None


def version_info():
    """Real local build info: the version pyproject.toml declares, and the git
    commit this checkout is on, if it's a git checkout. Never a fabricated
    "up to date" verdict — ADAPTIX has no update server to check against."""
    global _VERSION_INFO
    if _VERSION_INFO is not None:
        return _VERSION_INFO
    version = ''
    try:
        with open(os.path.join(ROOT, 'pyproject.toml'), encoding='utf-8') as handle:
            for line in handle:
                if line.strip().startswith('version'):
                    version = line.split('=', 1)[1].strip().strip('"\'')
                    break
    except OSError:
        pass
    commit = _git(['rev-parse', '--short', 'HEAD'])
    commit_date = _git(['log', '-1', '--format=%cI'])
    remote = _git(['remote', 'get-url', 'origin'])
    repo_url = remote[:-4] if remote.endswith('.git') else remote
    _VERSION_INFO = {'version': version, 'commit': commit, 'commit_date': commit_date, 'repo_url': repo_url}
    return _VERSION_INFO


def _flow_titles():
    data = _load_store('flow_titles')
    return data if isinstance(data, dict) else {}  # {run_id: title}


def _flow_favorites():
    return _load_store('flow_favorites')  # [run_id, ...]


def _flow_title_for(run_id, fallback):
    titles = _flow_titles()
    return titles.get(run_id) if isinstance(titles, dict) and titles.get(run_id) else fallback


def _run_ids():
    try:
        return sorted((n for n in os.listdir(os.path.join(CWD, 'artifacts', 'scans'))
                       if not n.startswith('.')), reverse=True)
    except OSError:
        return []


def _opencode_workspace(run_id):
    return os.path.join(_run_dir(run_id), 'external', 'pentest')


def _read_jsonl(path, limit=300):
    rows = []
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
                if len(rows) > limit:
                    rows.pop(0)
    except OSError:
        return []
    return rows


def _tail_text(path, max_lines=600, max_bytes=400_000):
    """Last N lines of a log file, bounded so a huge opencode log cannot stall a poll."""
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()
            data = handle.read()
    except OSError:
        return ''
    text = data.decode('utf-8', 'replace')
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return '\n'.join(lines)


def _opencode_terminals(run_id):
    base = _opencode_workspace(run_id)
    out = []
    activity_path = os.path.join(base, 'activity.ndjson')
    if os.path.isfile(activity_path):
        try:
            stat = os.stat(activity_path)
            out.append({'key': 'commands', 'label': 'Tool commands · readable',
                        'size': stat.st_size, 'mtime': stat.st_mtime})
        except OSError:
            pass
    for key, label, relative in TERMINALS:
        path = os.path.join(base, *relative.split('/'))
        if not os.path.isfile(path):
            continue
        try:
            stat = os.stat(path)
            out.append({'key': key, 'label': label, 'size': stat.st_size,
                        'mtime': stat.st_mtime})
        except OSError:
            continue
    return out


def _activity_text(run_id, max_rows=400):
    """The SQLite bridge's NDJSON rendered as a readable command terminal."""
    rows = _read_jsonl(os.path.join(_opencode_workspace(run_id), 'activity.ndjson'),
                       limit=max_rows)
    lines = []
    for row in rows:
        stamp = str(row.get('created_at') or '')[11:19]
        tool = row.get('tool') or row.get('agent') or 'event'
        summary = str(row.get('summary') or '').strip()
        lines.append(f'{stamp} [{tool}] {summary}')
        command = str(row.get('command') or '').strip()
        if command:
            lines.append(f'  $ {command}')
        exit_code = row.get('exit_code')
        if exit_code not in (None, ''):
            lines.append(f'  exit {exit_code}')
        excerpt = str(row.get('output_excerpt') or '').strip()
        if excerpt:
            for line in excerpt.splitlines()[:8]:
                lines.append(f'  | {line[:300]}')
        lines.append('')
    return '\n'.join(lines)


def _external_details(rows):
    """Map opencode-pentester findings onto the UI's finding detail shape."""
    return [{
        'endpoint': str(row.get('evidence_file') or ''),
        'parameter': '',
        'payload': '',
        'url': str(row.get('evidence_file') or ''),
        'class': 'external',
        'severity': str(row.get('severity') or 'info'),
        'status': 'external',
        'title': str(row.get('title') or ''),
        'cwe': str(row.get('cwe') or ''),
        'cause': str(row.get('description') or '')[:600],
        'mitigation': '',
        'impact': str(row.get('poc_output') or '')[:300],
        'extracted': [],
        'impact_proven': False,
    } for row in rows]


def _opencode_snapshot(run_id, base) -> LiveView:
    """Rebuild an external run from its own on-disk artifacts.

    A finished oc-* run has no LangGraph checkpoint, so the generic snapshot path
    showed an empty flow. Everything here is read from what the engine wrote: the
    report, the SQLite bridge's state.json, and the NDJSON activity/findings.
    """
    workspace = _opencode_workspace(run_id)
    report = Runner._latest_json(base, 'report-*.json') or {}
    view = view_from_report(report) if report else LiveView()
    try:
        with open(os.path.join(workspace, 'state', 'state.json'), encoding='utf-8') as handle:
            engine_state = json.load(handle)
    except (OSError, ValueError):
        engine_state = {}
    findings = _read_jsonl(os.path.join(workspace, 'findings.ndjson'))
    activity = _read_jsonl(os.path.join(workspace, 'activity.ndjson'), limit=300)
    insights = _read_jsonl(os.path.join(workspace, 'insights.jsonl'), limit=80)
    view.engine = 'opencode'
    view.run_id = run_id
    view.model = str(report.get('llm_model') or engine_state.get('model') or view.model)
    if not view.model:
        try:
            with open(os.path.join(workspace, 'run.sh'), encoding='utf-8') as handle:
                match = re.search(r"^MODEL='?([^'\n]+)'?$", handle.read(), re.M)
            if match:
                view.model = match.group(1).strip()
        except (OSError, ValueError):
            pass
    try:
        with open(os.path.join(workspace, 'exit-code'), encoding='utf-8') as handle:
            code = int((handle.read() or '0').strip() or 0)
        view.status = 'completed' if code == 0 else 'completed_with_errors'
        view.stop_reason = 'external_exit'
    except (OSError, ValueError):
        # No exit code yet. A run supervised by another process (or one that
        # outlived a UI restart) is still active while its poller keeps writing
        # state.json; without this the flow looked idle while it was scanning.
        try:
            age = time.time() - os.path.getmtime(os.path.join(workspace, 'state', 'state.json'))
            if age < 90:
                view.status = 'running'
        except OSError:
            pass
    target = report.get('target') or ([engine_state['target']] if engine_state.get('target') else [])
    if target:
        view.target = list(target) if isinstance(target, (list, tuple)) else [str(target)]
    view.full_offensive = bool((report.get('external_engine') or {}).get('full_offensive'))
    external = {
        'engine': 'opencode-pentester',
        'state': engine_state,
        'activity': activity,
        'findings': findings,
        'insights': insights,
        'workspace': workspace,
    }
    if report.get('external_metrics'):
        external['metrics'] = report['external_metrics']
    view.external = external
    view.details = _external_details(findings or (report.get('external_findings') or []))
    if report.get('status'):
        view.status = str(report['status'])
    return view


CODE_TERMINALS = (
    ('worker', 'Audit worker · log', 'logs/worker.log'),
    ('activity', 'Audit activity (NDJSON)', 'code-activity.ndjson'),
    ('report', 'Report (Markdown)', 'code-report.md'),
    ('bundle', 'Source bundle metadata', 'code-meta.json'),
)


def _is_code_run(run_id):
    base = _run_dir(run_id)
    return str(run_id).startswith('code-') or os.path.isfile(os.path.join(base, 'code-meta.json'))


def _code_terminals(run_id):
    base = _run_dir(run_id)
    out = []
    activity_path = os.path.join(base, 'code-activity.ndjson')
    if os.path.isfile(activity_path):
        try:
            stat = os.stat(activity_path)
            out.append({'key': 'commands', 'label': 'Audit activity · readable',
                        'size': stat.st_size, 'mtime': stat.st_mtime})
        except OSError:
            pass
    for key, label, relative in CODE_TERMINALS:
        path = os.path.join(base, *relative.split('/'))
        if not os.path.isfile(path):
            continue
        try:
            stat = os.stat(path)
            out.append({'key': key, 'label': label, 'size': stat.st_size,
                        'mtime': stat.st_mtime})
        except OSError:
            continue
    return out


def _flow_terminals(run_id):
    if _is_code_run(run_id):
        return _code_terminals(run_id)
    return _opencode_terminals(run_id)


def _code_activity_text(run_id, max_rows=400):
    rows = _read_jsonl(os.path.join(_run_dir(run_id), 'code-activity.ndjson'),
                       limit=max_rows)
    lines = []
    for row in rows:
        stamp = str(row.get('created_at') or '')[11:19]
        tool = row.get('tool') or 'audit'
        lines.append(f'{stamp} [{tool}] {row.get("status") or ""} {row.get("summary") or ""}'.rstrip())
        if row.get('target'):
            lines.append(f'  -> {row["target"]}')
        if row.get('id'):
            lines.append(f'  id {row["id"]}')
        lines.append('')
    return '\n'.join(lines)


def _code_snapshot(run_id, base) -> LiveView:
    """Rebuild a static audit from its own artifacts (no checkpoint exists)."""
    view = LiveView()
    view.engine = 'code'
    view.run_id = run_id
    meta = Runner._latest_json(base, 'code-meta.json') or {}
    progress = Runner._latest_json(base, 'code-progress.json') or {}
    report = Runner._latest_json(base, 'code-report.json') or {}
    if meta:
        view.objective = str(meta.get('instruction') or '')
        view.target = [str(meta.get('source_name') or 'source.zip')]
        view.model = str(meta.get('model') or '')
        view.max_iterations = int((meta.get('budgets') or {}).get('max_iterations') or 0)
    if report:
        view.status = str(report.get('status') or 'completed')
        view.stop_reason = str(report.get('stop_reason') or 'model_reported')
        view.model = str(report.get('llm_model') or view.model)
        view.details = code_details(report)
    elif progress:
        view.status = str(progress.get('status') or 'idle')
        view.stop_reason = str(progress.get('stop_reason') or '')
        view.iteration = int(progress.get('iterations') or 0)
        view.max_iterations = int(progress.get('max_iterations') or view.max_iterations)
        view.workflow_phase = str(progress.get('node') or 'audit')
    else:
        view.status = 'idle'
    view.workflow_node = 'code_audit'
    view.external = {
        'engine': 'code-audit',
        'meta': meta,
        'progress': progress,
        'report': report,
        'source': {'name': meta.get('source_name'), 'sha256': meta.get('source_sha256'),
                   'files': meta.get('files'), 'excluded': meta.get('excluded')} if meta else {},
    }
    try:
        view.log = _tail_text(os.path.join(base, 'logs', 'worker.log'), max_lines=200).splitlines()
    except OSError:
        view.log = []
    return view


def _run_snapshot(run_id) -> LiveView:
    """A read-only view of one run's latest saved state: its final report if it
    finished, otherwise its newest checkpoint. Never starts or touches a process."""
    base = _run_dir(run_id)
    if _is_code_run(run_id):
        return _code_snapshot(run_id, base)
    if run_id.startswith('oc-') or os.path.isdir(_opencode_workspace(run_id)):
        return _opencode_snapshot(run_id, base)
    report = Runner._latest_json(base, 'report-*.json')
    if report:
        view = view_from_report(report)
    else:
        view = LiveView()
        checkpoints = sorted(glob.glob(os.path.join(base, 'checkpoint-*.json')), key=os.path.getmtime)
        if checkpoints:
            try:
                with open(checkpoints[-1], encoding='utf-8') as handle:
                    state = json.load(handle)
                view = view_from_state(state, view)
            except (OSError, ValueError):
                pass
    view.run_id = run_id
    return view


def _view_json(view: LiveView, running: bool, total_runs=None):
    state = _checkpoint_state(_run_dir(view.run_id)) if view.run_id else {}
    if total_runs is None:
        total_runs = len(_run_ids())
    return {
        'running': running,
        'engine': getattr(view, 'engine', 'adaptix'),
        'full_offensive': bool(getattr(view, 'full_offensive', False)),
        'external': getattr(view, 'external', {}) or {},
        'terminals': _flow_terminals(view.run_id) if view.run_id else [],
        'target': view.target,
        'model': (getattr(view, 'opencode_model', '') or view.model)
                 if getattr(view, 'engine', 'adaptix') == 'opencode' else view.model,
        'run_id': view.run_id,
        'title': _flow_title_for(view.run_id, ''),
        'favorite': view.run_id in _flow_favorites(),
        'objective': view.objective,
        'status': view.status,
        'stop_reason': view.stop_reason,
        'iteration': view.iteration,
        'max_iterations': view.max_iterations,
        'elapsed': view.elapsed,
        'workflow_node': view.workflow_node,
        'workflow_phase': view.workflow_phase,
        'log': view.log[-500:],
        'details': view.details,
        'tokens': _token_json(view.tokens),
        'ledger': _ledger_from_state(state),
        'hypotheses': _hypotheses_from_state(state),
        'screenshots': _screenshots_from_state(state, view.run_id) if view.run_id else [],
        'searches': _searches_from_state(state),
        'tool_calls_used': int((state.get('execution_metrics') or {}).get('tool_calls_used') or 0),
        'total_runs': total_runs,
        'budgets': {'time': view.time_budget, 'tools': view.tool_budget,
                    'tokens': view.token_budget, 'context': view.context_tokens},
    }


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    # The code-audit upload is the only large body this UI accepts (4 MB ZIP plus
    # multipart overhead). Bounding it at the server prevents an unbounded read.
    app.config['MAX_CONTENT_LENGTH'] = 6_000_000

    @app.get('/')
    def index():
        return send_from_directory(STATIC_DIR, 'index.html')

    @app.errorhandler(413)
    def upload_too_large(_error):
        return jsonify({'error': 'unggahan terlalu besar (ZIP maksimal 4 MB)'}), 413

    @app.get('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory(STATIC_DIR, filename)

    @app.get('/api/version')
    def version():
        return jsonify(version_info())

    @app.get('/api/settings')
    def settings_get():
        account = _settings_json()
        model = configured_model()
        provider = model.split('/', 1)[0] if '/' in model else model
        context_tokens = str(os.getenv('ADAPTIX_MODEL_CONTEXT_TOKENS') or '').strip()
        timeout = str(os.getenv('ADAPTIX_LLM_TIMEOUT') or '').strip()
        return jsonify({
            'account': {
                'display_name': account['display_name'],
                'email': account['email'],
                'created_at': account['created_at'],
                'kind': 'Local account',
            },
            'providers': {
                'model': model or '(unset)',
                'provider': provider or '(unset)',
                'api_base': os.getenv('ADAPTIX_API_BASE') or '',
                'api_key': 'set' if os.getenv('ADAPTIX_API_KEY') else 'unset',
                'ollama_base': os.getenv('ADAPTIX_OLLAMA_BASE_URL') or '',
                'context_tokens': int(context_tokens) if context_tokens.isdigit() else '',
                'timeout': int(timeout) if timeout.isdigit() else '',
                'reasoning_effort': os.getenv('ADAPTIX_REASONING_EFFORT') or 'model default',
            },
            'prompts': [
                {'name': 'Planner',
                 'purpose': 'Chooses the next action and evidence-grounded hypotheses on every pass.',
                 'source': 'src/adaptix/agents/planner.py'},
                {'name': 'Provider probe',
                 'purpose': 'One-per-run JSON contract check before the first planning call.',
                 'source': 'src/adaptix/agents/provider_probe.py'},
                {'name': 'Report narrative',
                 'purpose': 'Turns verified findings into the final report prose.',
                 'source': 'src/adaptix/reporting/narrative.py'},
            ],
        })

    @app.post('/api/settings')
    def settings_save():
        body = request.get_json(force=True, silent=True) or {}
        data = _settings_json()
        if 'display_name' in body:
            name = str(body.get('display_name') or '').strip()[:60]
            if not name:
                return jsonify({'error': 'display name cannot be empty'}), 400
            data['display_name'] = name
        if 'email' in body:
            email = str(body.get('email') or '').strip()[:120]
            if not email or '@' not in email:
                return jsonify({'error': 'a valid email is required'}), 400
            data['email'] = email
        _save_store('settings', data)
        return jsonify({'account': {
            'display_name': data['display_name'], 'email': data['email'],
            'created_at': data['created_at'], 'kind': 'Local account',
        }})

    @app.get('/api/status')
    def status():
        if runner.running:
            runner.poll_artifacts(CWD)
        return jsonify(_view_json(runner.view, runner.running))

    @app.get('/api/runs')
    def runs():
        return jsonify({'runs': resumable_runs(CWD, limit=20)})

    @app.get('/api/analytics')
    def analytics():
        """Aggregate across every saved flow, not just the live one — real
        numbers read off each run's own checkpoint, nothing estimated."""
        import datetime
        ledger, daily, findings_total, tool_calls_total = [], {}, 0, 0
        hypotheses_total, duration_total = 0, 0.0
        run_ids = _run_ids()
        for run_id in run_ids:
            base = _run_dir(run_id)
            try:
                day = datetime.date.fromtimestamp(os.path.getctime(base)).isoformat()
            except OSError:
                day = None
            if day:
                daily[day] = daily.get(day, 0) + 1
            state = _checkpoint_state(base)
            ledger.extend(_ledger_from_state(state))
            findings_total += len(_run_snapshot(run_id).details)
            tool_calls_total += int((state.get('execution_metrics') or {}).get('tool_calls_used') or 0)
            hypotheses_total += len([row for row in (state.get('hypotheses') or []) if isinstance(row, dict)])
            duration_total += _run_seconds(base, state)
        charged = sum(r['charged'] for r in ledger)
        tokens_in = sum(r['prompt_tokens'] for r in ledger)
        tokens_out = sum(r['completion_tokens'] for r in ledger)
        cache_in = sum(r['cache_in'] for r in ledger)
        cache_out = sum(r['cache_out'] for r in ledger)
        total_cost = sum(r['total_cost'] for r in ledger if r['total_cost'] is not None)
        cost_known = all(r['total_cost'] is not None for r in ledger if r['prompt_tokens'] or r['completion_tokens'])
        return jsonify({
            'total_runs': len(run_ids),
            'llm_calls': len(ledger),
            'failed_calls': sum(1 for r in ledger if r['failed']),
            'cache_hits': sum(1 for r in ledger if r['cache_hit']),
            'total_tokens': charged,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'cache_in': cache_in,
            'cache_out': cache_out,
            'total_cost': total_cost,
            'cost_known': cost_known,
            'tool_calls_used': tool_calls_total,
            'hypotheses': hypotheses_total,
            'duration_seconds': round(duration_total, 1),
            'findings': findings_total,
            'ledger': ledger,
            'providers': _aggregate_usage(ledger, 'provider'),
            'models': _aggregate_usage(ledger, 'model'),
            'agents': _aggregate_usage(ledger, 'agent'),
            'tools': _tool_call_rows(run_ids),
            'daily': [{'date': d, 'count': c} for d, c in sorted(daily.items())],
        })

    @app.get('/api/flows')
    def flows():
        resumable = set(resumable_runs(CWD, limit=200))
        out = []
        for run_id in _run_ids()[:50]:
            is_live = run_id == runner.run_id
            view = runner.view if is_live else _run_snapshot(run_id)
            try:
                started_at = os.path.getctime(_run_dir(run_id))
            except OSError:
                started_at = 0
            out.append({'run_id': run_id, 'title': _flow_title_for(run_id, ''),
                        'favorite': run_id in _flow_favorites(),
                        'target': view.target, 'status': view.status,
                        'model': view.model, 'findings': len(view.details),
                        'objective': view.objective, 'started_at': started_at,
                        'resumable': run_id in resumable,
                        'live': run_id == runner.run_id and runner.running})
        return jsonify({'flows': out})

    @app.get('/api/flows/<run_id>')
    def flow_detail(run_id):
        if not os.path.isdir(_run_dir(run_id)):
            return jsonify({'error': 'no such flow'}), 404
        is_live = run_id == runner.run_id
        view = runner.view if is_live else _run_snapshot(run_id)
        return jsonify(_view_json(view, is_live and runner.running))

    @app.post('/api/flows/<run_id>/title')
    def flow_rename(run_id):
        if not os.path.isdir(_run_dir(run_id)):
            return jsonify({'error': 'no such flow'}), 404
        title = str((request.get_json(force=True, silent=True) or {}).get('title') or '').strip()[:120]
        titles = _flow_titles()
        if title:
            titles[run_id] = title
        else:
            titles.pop(run_id, None)
        _save_store('flow_titles', titles)
        return jsonify({'title': title})

    @app.post('/api/flows/<run_id>/favorite')
    def flow_favorite(run_id):
        if not os.path.isdir(_run_dir(run_id)):
            return jsonify({'error': 'no such flow'}), 404
        favorites = _flow_favorites()
        if run_id in favorites:
            favorites.remove(run_id)
            favorite = False
        else:
            favorites.append(run_id)
            favorite = True
        _save_store('flow_favorites', favorites)
        return jsonify({'favorite': favorite})

    @app.delete('/api/flows/<run_id>')
    def flow_delete(run_id):
        base = _run_dir(run_id)
        if not os.path.isdir(base):
            return jsonify({'error': 'no such flow'}), 404
        if run_id == runner.run_id and runner.running:
            return jsonify({'error': 'cannot delete a running flow; finish or cancel it first'}), 409
        import shutil
        shutil.rmtree(base)
        titles = _flow_titles(); titles.pop(run_id, None); _save_store('flow_titles', titles)
        favorites = _flow_favorites()
        if run_id in favorites:
            favorites.remove(run_id); _save_store('flow_favorites', favorites)
        return jsonify({'ok': True})

    @app.get('/api/flows/<run_id>/files')
    def flow_files(run_id):
        base = _run_dir(run_id)
        if not os.path.isdir(base):
            return jsonify({'error': 'no such flow'}), 404
        out = []
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                out.append({'name': name, 'size': os.path.getsize(path), 'mtime': os.path.getmtime(path)})
        return jsonify({'files': out})

    @app.get('/api/opencode/models')
    def opencode_model_list():
        """Models the local opencode install reports, for the flow dropdown."""
        models = opencode_models(refresh=True) if request.args.get('refresh') == '1' else peek_opencode_models()
        default = (os.getenv('ADAPTIX_OPENCODE_MODEL') or DEFAULT_OPENCODE_MODEL).strip()
        if default not in models:
            default = models[0] if models else ''
        return jsonify({'models': models, 'default': default})

    @app.get('/api/audit/models')
    def audit_model_list():
        """LiteLLM model choices for the static code audit."""
        configured = (os.getenv('ADAPTIX_LLM_MODEL') or '').strip()
        models = [m for m in (configured, 'deepseek/deepseek-chat',
                              'deepseek/deepseek-reasoner', 'ollama_chat/qwen3:14b') if m]
        models = list(dict.fromkeys(models))
        return jsonify({'models': models, 'default': configured or models[0]})

    @app.post('/api/audit/code')
    def audit_code():
        if runner.running:
            return jsonify({'error': 'a run is already active'}), 409
        upload = request.files.get('file')
        source_path = str(request.form.get('source_path') or '').strip()
        archive = None
        filename = ''
        if upload is not None and upload.filename:
            filename = secure_filename(upload.filename)
            if not filename.lower().endswith('.zip'):
                return jsonify({'error': 'hanya arsip .zip yang diterima'}), 400
            archive = upload.read(4_500_001)
            if len(archive) > 4_500_000:
                return jsonify({'error': 'ZIP maksimal 4 MB'}), 400
        elif not source_path:
            return jsonify({'error': 'unggah file ZIP atau isi path folder source'}), 400
        auto_patch = str(request.form.get('auto_patch') or '').lower() in ('1', 'true', 'on', 'yes')
        if auto_patch and not source_path:
            return jsonify({'error': 'patch otomatis hanya tersedia untuk folder lokal'}), 400
        instruction = str(request.form.get('instruction') or '').strip()
        if not instruction:
            return jsonify({'error': 'tuliskan tujuan audit kode'}), 400
        if len(instruction) > 12000:
            return jsonify({'error': 'tujuan audit maksimal 12000 karakter'}), 400
        model = (str(request.form.get('model') or '').strip()
                 or os.getenv('ADAPTIX_LLM_MODEL') or 'ollama_chat/qwen3:14b')
        def _budget(name, default, low, high):
            try:
                value = int(request.form.get(name) or default)
            except (TypeError, ValueError):
                value = default
            return max(low, min(high, value))
        budgets = {
            'time_budget': _budget('time_budget', 900, 30, 10800),
            'token_budget': _budget('token_budget', 50000, 1000, 2_000_000),
            'max_iterations': _budget('max_iterations', 8, 1, 30),
        }
        try:
            if source_path:
                run_id = start_code(runner, instruction, None, os.path.basename(source_path),
                                    model, budgets, source_path=source_path,
                                    auto_patch=auto_patch)
            else:
                run_id = start_code(runner, instruction, archive, filename, model, budgets)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        runner.engine = 'code'
        return jsonify(_view_json(runner.view, True))

    @app.get('/api/flows/<run_id>/terminals')
    def flow_terminals(run_id):
        if not os.path.isdir(_run_dir(run_id)):
            return jsonify({'error': 'no such flow'}), 404
        return jsonify({'terminals': _flow_terminals(run_id)})

    @app.get('/api/flows/<run_id>/terminal/<key>')
    def flow_terminal(run_id, key):
        if not os.path.isdir(_run_dir(run_id)):
            return jsonify({'error': 'no such flow'}), 404
        if key == 'commands':
            text = (_code_activity_text(run_id) if _is_code_run(run_id)
                    else _activity_text(run_id))
            return jsonify({'key': key, 'label': 'Activity · readable',
                            'exists': bool(text), 'size': len(text.encode('utf-8')),
                            'text': text})
        if _is_code_run(run_id):
            entry = next((row for row in CODE_TERMINALS if row[0] == key), None)
            base = _run_dir(run_id)
        else:
            entry = next((row for row in TERMINALS if row[0] == key), None)
            base = _opencode_workspace(run_id)
        if entry is None:
            return jsonify({'error': 'unknown terminal'}), 404
        path = os.path.join(base, *entry[2].split('/'))
        if not os.path.isfile(path):
            return jsonify({'key': key, 'label': entry[1], 'exists': False, 'text': ''})
        try:
            lines = max(50, min(2000, int(request.args.get('lines') or 600)))
        except ValueError:
            lines = 600
        return jsonify({'key': key, 'label': entry[1], 'exists': True,
                        'size': os.path.getsize(path),
                        'text': _tail_text(path, max_lines=lines)})

    @app.get('/api/flows/<run_id>/file/<path:filename>')
    def flow_file(run_id, filename):
        base = _run_dir(run_id)
        if not os.path.isdir(base):
            return abort(404)
        # send_from_directory itself rejects any path that escapes `base`.
        return send_from_directory(base, filename)

    # ---------------------------------------------------------- templates ---
    @app.get('/api/templates')
    def templates_list():
        return jsonify({'templates': _load_store('templates')})

    @app.post('/api/templates')
    def templates_create():
        body = request.get_json(force=True, silent=True) or {}
        name = str(body.get('name') or '').strip()
        objective = str(body.get('objective') or '').strip()
        if not name or not objective:
            return jsonify({'error': 'name and objective are required'}), 400
        item = {'id': secrets.token_hex(4), 'name': name, 'objective': objective,
                'target': str(body.get('target') or '').strip(),
                'model': str(body.get('model') or '').strip()}
        items = _load_store('templates')
        items.insert(0, item)
        _save_store('templates', items)
        return jsonify(item)

    @app.delete('/api/templates/<item_id>')
    def templates_delete(item_id):
        items = [t for t in _load_store('templates') if t.get('id') != item_id]
        _save_store('templates', items)
        return jsonify({'ok': True})

    # ---------------------------------------------------------- knowledge ---
    @app.get('/api/knowledge')
    def knowledge_list():
        return jsonify({'knowledge': _load_store('knowledge')})

    @app.post('/api/knowledge')
    def knowledge_create():
        body = request.get_json(force=True, silent=True) or {}
        title = str(body.get('title') or '').strip()
        content = str(body.get('content') or '').strip()
        if not title or not content:
            return jsonify({'error': 'title and content are required'}), 400
        item = {'id': secrets.token_hex(4), 'title': title, 'content': content}
        items = _load_store('knowledge')
        items.insert(0, item)
        _save_store('knowledge', items)
        return jsonify(item)

    @app.delete('/api/knowledge/<item_id>')
    def knowledge_delete(item_id):
        items = [k for k in _load_store('knowledge') if k.get('id') != item_id]
        _save_store('knowledge', items)
        return jsonify({'ok': True})

    # ---------------------------------------------------------- resources ---
    @app.get('/api/resources')
    def resources_list():
        try:
            names = sorted(os.listdir(RESOURCES_DIR))
        except OSError:
            names = []
        out = []
        for name in names:
            path = os.path.join(RESOURCES_DIR, name)
            if os.path.isfile(path):
                out.append({'name': name, 'size': os.path.getsize(path), 'mtime': os.path.getmtime(path)})
        return jsonify({'resources': out})

    @app.post('/api/resources')
    def resources_upload():
        file = request.files.get('file')
        if not file or not file.filename:
            return jsonify({'error': 'no file given'}), 400
        name = secure_filename(file.filename)
        if not name:
            return jsonify({'error': 'invalid filename'}), 400
        os.makedirs(RESOURCES_DIR, exist_ok=True)
        file.save(os.path.join(RESOURCES_DIR, name))
        return jsonify({'name': name})

    @app.get('/api/resources/<path:filename>')
    def resources_download(filename):
        return send_from_directory(RESOURCES_DIR, filename)

    @app.delete('/api/resources/<path:filename>')
    def resources_delete(filename):
        name = secure_filename(filename)
        path = os.path.join(RESOURCES_DIR, name)
        if os.path.isfile(path):
            os.remove(path)
        return jsonify({'ok': True})

    @app.post('/api/start')
    def start():
        if runner.running:
            return jsonify({'error': 'a run is already active'}), 409
        body = request.get_json(force=True, silent=True) or {}
        engine = str(body.get('engine') or 'adaptix').strip().lower()
        if engine not in ('adaptix', 'opencode'):
            return jsonify({'error': 'unknown engine'}), 400
        instruction = str(body.get('instruction') or '').strip()
        target = str(body.get('target') or '').strip()
        if not instruction and engine == 'adaptix':
            return jsonify({'error': 'instruction is required'}), 400
        if not target and not body.get('resume'):
            return jsonify({'error': 'target is required'}), 400
        if not instruction:
            instruction = f'Authorized security assessment of {target}'
        if engine == 'opencode' and body.get('full_offensive'):
            host = urlsplit(target if '://' in target else 'http://' + target).hostname or ''
            if not body.get('authorized'):
                return jsonify({'error': 'full offensive requires the written-authorization confirmation'}), 400
            if str(body.get('confirm_target') or '').strip() != host:
                return jsonify({'error': f'type the target host "{host}" to confirm full offensive'}), 400
        knowledge_ids = body.get('knowledge_ids') or []
        if knowledge_ids:
            notes = [k for k in _load_store('knowledge') if k.get('id') in knowledge_ids]
            if notes:
                prefix = '\n\n'.join(f"[{n['title']}] {n['content']}" for n in notes)
                instruction = prefix + '\n\n' + instruction
        view = runner.view
        view.target = [target] if target else view.target
        view.model = str(body.get('model') or view.model)
        view.engine = engine
        view.full_offensive = bool(body.get('full_offensive')) if engine == 'opencode' else False
        view.focus = str(body.get('focus') or '').strip()
        view.opencode_model = str(body.get('opencode_model') or '').strip()
        view.reviewer = body.get('reviewer', True) is not False
        view.external = {}
        runner.engine = engine
        resource_name = str(body.get('identity_resource') or '').strip()
        view.identity = os.path.join(RESOURCES_DIR, secure_filename(resource_name)) if resource_name else str(body.get('identity') or view.identity)
        for key, attr in (('time_budget', 'time_budget'), ('tool_budget', 'tool_budget'),
                          ('token_budget', 'token_budget'), ('context_tokens', 'context_tokens')):
            if key in body:
                setattr(view, attr, None if body[key] in (None, 'unlimited') else int(body[key]))
        runner.resume_run_id = str(body.get('resume') or '') if engine == 'adaptix' else ''
        runner.start(instruction, CWD)
        return jsonify(_view_json(runner.view, runner.running))

    @app.post('/api/cancel')
    def cancel():
        runner.cancel()
        return jsonify({'ok': True})

    return app


def main(host='127.0.0.1', port=8420):
    app = create_app()
    print(f'ADAPTIX web UI: http://{host}:{port}')
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == '__main__':
    main()
