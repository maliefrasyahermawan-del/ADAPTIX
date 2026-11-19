"""Run opencode-pentester as an ADAPTIX external engine inside one isolated workspace.

This module is deliberately a thin supervisor:
  * it prepares a per-run workspace (skill copy, PENTEST_HOME, DB, outputs),
  * launches opencode in WSL with the engagement already initialised,
  * tails the human-readable log plus the SQLite bridge (activity/state/gate),
  * asks a read-only reviewer model for concise insights,
  * writes ADAPTIX-compatible progress/report artifacts.

It never executes target commands itself; opencode-pentester does, under its own
scope guard and the per-run DB. ADAPTIX owns isolation, streaming, insight and cancel.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from src.adaptix.config import ROOT

ANSI = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')
DEFAULT_OPENCODE_MODEL = 'deepseek/deepseek-flash'
REVIEW_INTERVAL = 18.0
REVIEW_MIN_NEW = 3
REVIEW_MAX_CALLS = 30
REVIEW_MAX_TOKENS = 60000

# Curated fallback so the dropdown is still useful when `opencode models` cannot
# run (offline, not authenticated yet, or a cold WSL). DeepSeek first because the
# operator's working setup uses it.
CURATED_OPENCODE_MODELS = (
    'deepseek/deepseek-flash',
    'opencode/deepseek-v4.1-flash-free',
    'deepseek/deepseek-v4-pro',
    'opencode/big-pickle',
    'opencode/beam-free',
    'opencode/hy4-flash-free',
    'opencode/longcat-2.5-free',
    'opencode/mimo-v2.6-flash-free',
    'opencode/nemotron-3.5-lightning-free',
)
_MODELS_CACHE = {'at': 0.0, 'models': []}
_MODELS_TTL = 300.0

# Terminal files this engine writes. The UI lists them so an operator can open
# the exact stream (opencode run, the preflight, the SQLite bridge) instead of a
# single merged log. Paths are relative to the per-run workspace.
TERMINALS = (
    ('opencode', 'OpenCode run · raw logs', 'logs/opencode.log'),
    ('session', 'OpenCode run · session output', 'live.log'),
    ('init', 'Engine init & preflight', 'logs/init.log'),
    ('poller', 'SQLite bridge · poller', 'logs/poller.log'),
    ('reviewer', 'Reviewer model', 'logs/reviewer.log'),
    ('activity', 'Tool activity (NDJSON)', 'activity.ndjson'),
    ('findings', 'External findings (NDJSON)', 'findings.ndjson'),
    ('state', 'Engine state (JSON)', 'state/state.json'),
)


def peek_opencode_models():
    """Models for UI: cached/live list, or the curated list while a probe runs.

    `opencode models` takes a few seconds on a cold WSL; a dropdown must not wait
    for it. The first caller gets a usable list immediately and a background
    refresh replaces it for the next poll.
    """
    if _MODELS_CACHE['models']:
        return list(_MODELS_CACHE['models'])
    threading.Thread(target=opencode_models, daemon=True).start()
    return list(CURATED_OPENCODE_MODELS)


def _wsl_bash(command: str, timeout=60):
    """Run a bash command in the default WSL distribution; return stdout text."""
    try:
        done = subprocess.run(['wsl.exe', '-e', 'bash', '-lc', command],
                              capture_output=True, text=True, timeout=timeout)
        return done.stdout if done.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def opencode_models(refresh=False):
    """Models the local opencode install can actually serve, DeepSeek first.

    Reads the real install (`opencode models`) instead of inventing a list; the
    curated list is only a fallback and is clearly a fallback, never mixed in as
    if it were the live answer.
    """
    now = time.time()
    if not refresh and _MODELS_CACHE['models'] and now - _MODELS_CACHE['at'] < _MODELS_TTL:
        return _MODELS_CACHE['models']
    output = _wsl_bash('"$HOME/.opencode/bin/opencode" models 2>&1 || opencode models 2>&1', timeout=90)
    models = []
    for raw in output.splitlines():
        name = ANSI.sub('', raw).strip()
        if not name or ' ' in name or '/' not in name:
            continue
        if name in ('provider/model',):
            continue
        models.append(name)
    if not models:
        models = list(CURATED_OPENCODE_MODELS)
    else:
        models = list(dict.fromkeys(models))
    models.sort(key=lambda name: (0 if 'deepseek' in name.lower() else 1, name))
    _MODELS_CACHE.update({'at': now, 'models': models})
    return models


def wsl_path(path: Path) -> str:
    path = Path(path).resolve()
    drive = (path.drive or 'C:')[0].lower()
    rest = str(path)[2:].replace('\\', '/')
    return f'/mnt/{drive}{rest}'


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _read_new_jsonl(path: Path, offset: int):
    rows = []
    try:
        with path.open('rb') as handle:
            handle.seek(offset)
            data = handle.read()
        offset += len(data)
        for raw in data.decode('utf-8', 'replace').splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except ValueError:
                continue
    except OSError:
        pass
    return rows, offset


def _iso_now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _review_prompt(activities, state):
    lines = []
    for row in activities[-12:]:
        command = str(row.get('command') or row.get('summary') or '')[:400]
        excerpt = str(row.get('output_excerpt') or '')[:1200]
        lines.append(
            f"- id={row.get('id')} phase={row.get('phase') or '-'} agent={row.get('agent') or '-'} "
            f"tool={row.get('tool') or '-'} exit={row.get('exit_code')} duration_ms={row.get('duration_ms')}\n"
            f"  command: {command}\n  output: {excerpt}")
    gate = state.get('gate') or {}
    pending = [f"[{p.get('phase')}] {p.get('item')}" for p in (gate.get('pending') or [])[:8]]
    return (
        'You are a read-only reviewer observing an autonomous penetration test. '
        'Do not execute anything, do not invent vulnerabilities, and do not claim something is '
        'confirmed unless the command output proves it. Explain what is happening, what the recent '
        'commands actually establish, anomalies, dead ends, and the best next checks. '
        'Return ONLY JSON with this shape: '
        '{"headline": string, "current_activity": string, '
        '"insights": [{"kind": "signal|risk|opportunity|dead_end", "title": string, '
        '"detail": string, "confidence": number, "next_step": string}], '
        '"coverage_gaps": [string], "anomalies": [string]}. '
        'Maximum 4 insights. Keep each detail under 450 characters. '
        f'\n\nEngagement state: {json.dumps({k: state.get(k) for k in ("state", "status", "counts", "severity")})}'
        f'\nGate pending: {pending}'
        f'\nRecent activity:\n' + '\n'.join(lines)
    )


def _review_log(insight_path: Path, message: str):
    try:
        with (insight_path.parent.parent / 'logs' / 'reviewer.log').open('a', encoding='utf-8') as handle:
            handle.write(f'{_iso_now()} {message}\n')
    except OSError:
        pass


def _run_reviewer(runner, activities, state, insight_path: Path):
    try:
        import litellm
    except Exception:
        return
    external = runner.view.external
    if external.get('review_calls', 0) >= REVIEW_MAX_CALLS:
        return
    if external.get('review_tokens', 0) >= REVIEW_MAX_TOKENS:
        return
    model = (os.getenv('ADAPTIX_REVIEWER_MODEL') or '').strip()
    if not model:
        from src.adaptix.ui.runner import configured_model
        model = configured_model()
    if not model:
        return
    messages = [
        {'role': 'system', 'content': 'You are a concise, evidence-grounded security reviewer. Return JSON only.'},
        {'role': 'user', 'content': _review_prompt(activities, state)},
    ]
    try:
        response = litellm.completion(
            model=model, messages=messages, temperature=0.2, max_tokens=900, timeout=60,
            api_key=os.getenv('ADAPTIX_API_KEY') or None,
            api_base=os.getenv('ADAPTIX_API_BASE') or None,
        )
        content = response.choices[0].message.content or ''
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip(), flags=re.I)
        payload = json.loads(content)
    except Exception as exc:
        runner.view.external['reviewer_error'] = f'{type(exc).__name__}: {exc}'[:300]
        _review_log(insight_path, f'reviewer error: {type(exc).__name__}: {exc}'[:500])
        return
    insights = payload.get('insights') if isinstance(payload, dict) else None
    if not isinstance(insights, list):
        return
    stamp = _iso_now()
    record = {
        'id': f'rev-{int(time.time() * 1000)}',
        'created_at': stamp,
        'headline': str(payload.get('headline') or '')[:300],
        'current_activity': str(payload.get('current_activity') or '')[:300],
        'coverage_gaps': [str(x)[:300] for x in (payload.get('coverage_gaps') or [])][:6],
        'anomalies': [str(x)[:300] for x in (payload.get('anomalies') or [])][:6],
        'insights': [],
        'model': model,
    }
    for item in insights[:4]:
        if not isinstance(item, dict):
            continue
        record['insights'].append({
            'kind': str(item.get('kind') or 'signal')[:20],
            'title': str(item.get('title') or '')[:200],
            'detail': str(item.get('detail') or '')[:700],
            'confidence': item.get('confidence'),
            'next_step': str(item.get('next_step') or '')[:300],
        })
    try:
        with insight_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + '\n')
    except OSError:
        pass
    external.setdefault('insights', []).append(record)
    external['insights'] = external['insights'][-80:]
    _review_log(insight_path, f'{model} -> {len(record["insights"])} insight(s)')
    external['review_calls'] = int(external.get('review_calls', 0)) + 1
    usage = getattr(response, 'usage', None)
    if usage is not None:
        used = 0
        if isinstance(usage, dict):
            used = int(usage.get('total_tokens') or 0)
        else:
            used = int(getattr(usage, 'total_tokens', 0) or 0)
        external['review_tokens'] = int(external.get('review_tokens', 0)) + used


def _write_report(runner, workspace: Path, external: dict, exit_code, elapsed):
    findings = list(external.get('findings') or [])
    state = external.get('state') or {}
    gate = state.get('gate') or {}
    report = {
        'status': 'completed' if exit_code == 0 else 'completed_with_errors',
        'mode': 'opencode-pentester',
        'engine': 'opencode-pentester',
        'external_engine': {
            'name': 'opencode-pentester',
            'full_offensive': bool(runner.view.full_offensive),
            'model': runner.view.opencode_model,
            'engagement': external.get('engagement'),
            'workspace': str(workspace),
            'elapsed_seconds': round(elapsed, 1),
            'exit_code': exit_code,
        },
        'target': runner.view.target,
        'llm_model': runner.view.opencode_model,
        'verified_findings': [],
        'external_findings': findings,
        'findings': findings,
        'scanner_matched_findings': [],
        'rejected_findings': [],
        'inconclusive_findings': [],
        'hypotheses': [],
        'external_metrics': {
            'commands': (state.get('counts') or {}).get('commands'),
            'hosts': (state.get('counts') or {}).get('hosts'),
            'services': (state.get('counts') or {}).get('services'),
            'vulns': (state.get('counts') or {}).get('vulns'),
            'leads_open': (state.get('counts') or {}).get('leads_open'),
            'gate': gate,
            'review_calls': external.get('review_calls'),
            'review_tokens': external.get('review_tokens'),
        },
        'termination': {'stop_reason': 'external_exit', 'exit_code': exit_code},
        'budget_status': {},
        'stop_reason': 'external_exit',
        'narrative': {},
        'errors': [],
        'disclaimer': 'Findings produced by opencode-pentester are external evidence and are not '
                      'independently verified by ADAPTIX.',
    }
    digest = abs(hash(json.dumps(report, sort_keys=True, default=str))) & 0xFFFFFFFFFFFF
    path = workspace.parent.parent / f'report-{digest:012x}.json'
    try:
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    except OSError:
        pass
    runner.view.details = [{
        'endpoint': str(row.get('evidence_file') or ''),
        'parameter': '',
        'payload': '',
        'url': str(row.get('evidence_file') or ''),
        'class': 'external',
        'severity': str(row.get('severity') or 'info'),
        'status': 'external',
        'title': str(row.get('title') or ''),
        'cwe': '',
        'cause': str(row.get('description') or '')[:600],
        'mitigation': '',
        'impact': str(row.get('poc_output') or '')[:300],
        'extracted': [],
        'impact_proven': False,
    } for row in findings]


def start_opencode(runner, instruction: str):
    """Prepare and launch one isolated opencode-pentester engagement."""
    view = runner.view
    runner.run_id = time.strftime('oc-%H%M%S')
    view.run_id = runner.run_id
    view.objective = instruction
    view.status = 'starting'
    view.stop_reason = ''
    view.log = []
    view.details = []
    view.started_at = time.time()
    view.engine = 'opencode'
    view.workflow_node = 'opencode'
    view.workflow_phase = 'starting'
    view.external = {'activity': [], 'insights': [], 'findings': [], 'review_calls': 0,
                     'review_tokens': 0, 'engine': 'opencode-pentester'}
    view.append(f'objective: {instruction[:160]}')

    run_root = ROOT / 'artifacts' / 'scans' / runner.run_id
    workspace = run_root / 'external' / 'pentest'
    for name in ('db', 'outputs', 'state', 'logs', '.opencode/skills'):
        (workspace / name).mkdir(parents=True, exist_ok=True)
    (run_root / 'external').mkdir(parents=True, exist_ok=True)
    (run_root / 'external' / 'approval.json').write_text(json.dumps({
        'engine': 'opencode-pentester',
        'target': (view.target or [''])[0],
        'full_offensive': bool(view.full_offensive),
        'authorized': bool(view.full_offensive),
        'reviewer': bool(view.reviewer),
        'model': view.opencode_model,
        'recorded_at': _iso_now(),
    }, indent=2), encoding='utf-8')
    skill_src = ROOT / 'vendor' / 'opencode-pentester'
    skill_dst = workspace / '.opencode' / 'skills' / 'opencode-pentester'
    if not skill_src.is_dir():
        raise FileNotFoundError(f'opencode-pentester vendor bundle missing: {skill_src}')

    target = (view.target or [''])[0]
    parsed = urlsplit(target if '://' in target else 'http://' + target)
    host = parsed.hostname or ''
    engagement = f'adaptix-{runner.run_id}'
    minutes = max(1, int(round((view.time_budget or 300) / 60.0)))
    model = (view.opencode_model or os.getenv('ADAPTIX_OPENCODE_MODEL') or DEFAULT_OPENCODE_MODEL).strip()
    view.opencode_model = model
    view.model = model
    thoroughness = 'Maximum' if view.full_offensive else 'Deep'
    focus = (view.focus or '').strip()
    prompt = (
        f'I have written authorization to test {target}. Use the opencode-pentester skill. '
        f'Target: {target}. Time budget: {minutes} minutes. Thoroughness: {thoroughness}. '
        f'The engagement id {engagement} is already initialized and its scope is recorded; '
        'do not ask for the target, scope, budget or authorization and do not run find-target. '
        'Continue with recon, testing, verification and reporting. Log every tool run with findings.sh. '
    )
    if focus:
        prompt += f'Focus domains: {focus}. '
    if view.full_offensive:
        prompt += (f'--full-offensive --time {minutes}. Use all categories at maximum depth, including '
                   'exploitation, but keep every action inside the recorded target scope. ')
    else:
        prompt += ('Do not use --full-offensive. Stay non-destructive: no exploit, post-exploit, '
                   'DoS, social engineering, or state-changing requests. ')
    prompt += 'Keep going until the time budget is exhausted or the deterministic gate passes. '

    prompt_path = workspace / 'prompt.txt'
    prompt_path.write_text(prompt, encoding='utf-8')
    (workspace / 'opencode.json').write_text(json.dumps({
        '$schema': 'https://opencode.ai/config.json',
        # A pentest run must never block on an interactive question: the skill is
        # told the target, scope and budget up front. `--auto` covers the rest.
        'permission': {'question': 'deny', 'bash': 'allow', 'edit': 'allow', 'write': 'allow'},
    }, indent=2), encoding='utf-8')

    script = f'''#!/usr/bin/env bash
set -u
WS={shlex.quote(wsl_path(workspace))}
SKILL={shlex.quote(wsl_path(skill_src))}
SKILL_LOCAL="$WS/.opencode/skills/opencode-pentester"
ENG={shlex.quote(engagement)}
TARGET={shlex.quote(target)}
SCOPE={shlex.quote(host)}
MINUTES={minutes}
MODEL={shlex.quote(model)}
export PENTEST_HOME="$WS/db"
export PENTEST_DB="$WS/db/findings.db"
export PENTEST_OUTPUTS="$WS/outputs"
export PENTEST_ENGAGEMENT="$ENG"
export PENTEST_ALLOW_PRIVATE=1
export PYTHONUNBUFFERED=1
export OPENCODE_DB="$WS/opencode.db"
ENV_FILE={shlex.quote(wsl_path(ROOT / '.env'))}
if [ -z "${{DEEPSEEK_API_KEY:-}}" ] && [ -f "$ENV_FILE" ]; then
  DEEPSEEK_API_KEY="$(grep '^ADAPTIX_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '\r')"
  export DEEPSEEK_API_KEY
fi
# The native Linux opencode is the one that can run this skill's bash tooling.
# The Windows npm shim lives under /mnt/c and is only a last resort.
export PATH="$HOME/.opencode/bin:/usr/local/bin:$PATH"
OPENCODE_BIN="${{ADAPTIX_OPENCODE_BIN:-}}"
if [ -z "$OPENCODE_BIN" ]; then
  for c in "$HOME/.opencode/bin/opencode" /usr/local/bin/opencode; do
    if [ -x "$c" ]; then OPENCODE_BIN="$c"; break; fi
  done
fi
if [ -z "$OPENCODE_BIN" ]; then
  CAND="$(command -v opencode 2>/dev/null || true)"
  case "$CAND" in /mnt/*) : ;; *) OPENCODE_BIN="$CAND" ;; esac
fi
mkdir -p "$WS/db" "$WS/outputs" "$WS/state" "$WS/logs" "$WS/.opencode/skills"
: > "$WS/logs/opencode.log"
: > "$WS/logs/reviewer.log"
if [ -z "$OPENCODE_BIN" ] || [ ! -x "$OPENCODE_BIN" ]; then
  echo "opencode binary not found (expected $HOME/.opencode/bin/opencode)" | tee -a "$WS/live.log"
  echo 127 > "$WS/exit-code"
  touch "$WS/stop-poller"
  exit 127
fi
rm -rf "$SKILL_LOCAL"
cp -a "$SKILL" "$SKILL_LOCAL"
cd "$WS" || exit 1
echo "opencode $("$OPENCODE_BIN" --version 2>/dev/null) model $MODEL" >>"$WS/live.log"
bash "$SKILL_LOCAL/db/findings.sh" init "$ENG" --scope "$SCOPE" --target "$TARGET" --force >"$WS/logs/init.log" 2>&1
bash "$SKILL_LOCAL/db/findings.sh" budget init "$MINUTES" >>"$WS/logs/init.log" 2>&1 || true
bash "$SKILL_LOCAL/db/findings.sh" state transit recon >>"$WS/logs/init.log" 2>&1 || true
MISSING=0
for t in curl nmap ffuf nuclei python3; do command -v "$t" >/dev/null || MISSING=1; done
if [ "$MISSING" = "0" ]; then
  bash "$SKILL_LOCAL/db/findings.sh" log doctor preflight "PASS: ADAPTIX lab preflight (curl,nmap,ffuf,nuclei,python3)" >>"$WS/logs/init.log" 2>&1 || true
else
  bash "$SKILL_LOCAL/db/findings.sh" log doctor preflight "FAIL: ADAPTIX lab preflight missing required tool" >>"$WS/logs/init.log" 2>&1 || true
fi
python3 {shlex.quote(wsl_path(ROOT / 'src' / 'adaptix' / 'opencode_poller.py'))} "$WS" "$ENG" "$SKILL_LOCAL" >"$WS/logs/poller.log" 2>&1 &
POLLER=$!
echo "workspace $WS" >>"$WS/live.log"
echo "engagement $ENG target $TARGET model $MODEL budget ${{MINUTES}}m" >>"$WS/live.log"
PROMPT="$(cat "$WS/prompt.txt")"
# A run may not outlive its advertised budget by more than a short grace period;
# without a hard guard a provider error loop kept the process alive indefinitely.
timeout $((MINUTES * 60 + 180)) "$OPENCODE_BIN" run --auto --print-logs --log-level INFO -m "$MODEL" "$PROMPT" 2>>"$WS/logs/opencode.log" | tee -a "$WS/live.log"
RC=${{PIPESTATUS[0]}}
kill "$POLLER" 2>/dev/null || true
echo "$RC" > "$WS/exit-code"
touch "$WS/stop-poller"
exit "$RC"
'''
    script_path = workspace / 'run.sh'
    script_path.write_text(script, encoding='utf-8', newline='\n')

    activity_path = workspace / 'activity.ndjson'
    findings_path = workspace / 'findings.ndjson'
    insights_path = workspace / 'insights.jsonl'
    state_path = workspace / 'state' / 'state.json'

    proc = subprocess.Popen(
        ['wsl.exe', '-e', 'bash', wsl_path(script_path)],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        bufsize=1, env=dict(os.environ, PYTHONUNBUFFERED='1'))
    runner.process = proc

    def work():
        offsets = {'activity': 0, 'findings': 0, 'insights': 0}
        last_review = 0.0
        last_review_count = 0
        state = {}
        try:
            for raw in proc.stdout or []:
                line = ANSI.sub('', raw).rstrip()
                if not line:
                    continue
                view.append(line[:1200])
            code = proc.wait()
        except Exception as exc:
            code = -1
            view.append(f'opencode runner error: {type(exc).__name__}: {exc}'[:500])
        elapsed = time.time() - (view.started_at or time.time())
        # final drains
        rows, offsets['activity'] = _read_new_jsonl(activity_path, offsets['activity'])
        if rows:
            view.external['activity'].extend(rows)
            view.external['activity'] = view.external['activity'][-300:]
        rows, offsets['findings'] = _read_new_jsonl(findings_path, offsets['findings'])
        if rows:
            view.external['findings'].extend(rows)
            view.external['findings'] = view.external['findings'][-200:]
        rows, offsets['insights'] = _read_new_jsonl(insights_path, offsets['insights'])
        if rows:
            view.external['insights'].extend(rows)
            view.external['insights'] = view.external['insights'][-80:]
        final_state = _read_json(state_path)
        if final_state:
            state = final_state
            view.external['state'] = final_state
        try:
            _write_report(runner, workspace, view.external, code, elapsed)
        except Exception as exc:
            view.append(f'report write failed: {type(exc).__name__}: {exc}'[:300])
        view.status = 'completed' if code == 0 else 'completed_with_errors'
        view.stop_reason = 'external_exit'
        view.workflow_phase = 'completed'
        view.append(f'run finished (exit {code})')
        runner.finished.set()

    def poller():
        offsets = {'activity': 0, 'findings': 0, 'insights': 0}
        last_review = 0.0
        last_review_count = 0
        state = {}
        while proc.poll() is None:
            rows, offsets['activity'] = _read_new_jsonl(activity_path, offsets['activity'])
            if rows:
                view.external['activity'].extend(rows)
                view.external['activity'] = view.external['activity'][-300:]
            rows, offsets['findings'] = _read_new_jsonl(findings_path, offsets['findings'])
            if rows:
                view.external['findings'].extend(rows)
                view.external['findings'] = view.external['findings'][-200:]
            rows, offsets['insights'] = _read_new_jsonl(insights_path, offsets['insights'])
            if rows:
                view.external['insights'].extend(rows)
                view.external['insights'] = view.external['insights'][-80:]
            state = _read_json(state_path)
            if state:
                view.external['state'] = state
                view.status = 'running'
                view.workflow_phase = str(state.get('state') or 'running')
                counts = state.get('counts') or {}
                view.iteration = int(counts.get('commands') or 0)
                last = state.get('last_activity') or {}
                view.workflow_node = str(last.get('tool') or last.get('agent') or 'opencode')
            activity = view.external.get('activity') or []
            if (view.reviewer and len(activity) - last_review_count >= REVIEW_MIN_NEW
                    and time.time() - last_review >= REVIEW_INTERVAL
                    and activity):
                last_review = time.time()
                last_review_count = len(activity)
                threading.Thread(
                    target=_run_reviewer,
                    args=(runner, activity[-12:], state or view.external.get('state') or {}, insights_path),
                    daemon=True).start()
            time.sleep(1.0)

    runner.thread = threading.Thread(target=work, daemon=True)
    runner.thread.start()
    threading.Thread(target=poller, daemon=True).start()


def kill_opencode(runner):
    proc = getattr(runner, 'process', None)
    workspace = ROOT / 'artifacts' / 'scans' / runner.run_id / 'external' / 'pentest'
    if proc is None or proc.poll() is not None:
        return
    try:
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                       capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.terminate()
        except OSError:
            pass
    # taskkill ends the Windows wsl.exe relay; the native opencode child can
    # outlive it. Kill only this run's workspace so a parallel run is untouched.
    try:
        subprocess.run(['wsl.exe', '-e', 'bash', '-lc',
                        f'pkill -f {shlex.quote(wsl_path(workspace))} 2>/dev/null || true'],
                       capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        (workspace / 'stop-poller').touch()
    except OSError:
        pass
