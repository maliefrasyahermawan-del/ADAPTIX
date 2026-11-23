"""Shared run controller: launches one assessment as a subprocess and polls its
artifacts (progress/checkpoint/report JSON) into a ``LiveView``.

Pulled out of ``ui/screen.py`` so the web UI can reuse it without importing
``curses`` (unavailable on Windows and in headless environments).
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import threading
import time

from src.adaptix.ui.state import (LiveView, read_tokens, view_from_progress,
                                  view_from_report, view_from_state)
from src.adaptix.workflow.budget import UNLIMITED_WORD, parse_budget

_ANSI = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]')
_PROVIDER_NOISE = ('Provider List:', 'LLM Provider NOT provided',
                   'Pass model as E.g.', 'Give Feedback', 'Get help')


def budget_argument(value) -> str:
    return UNLIMITED_WORD if value is None else str(value)


def configured_model():
    return (os.getenv('ADAPTIX_LLM_MODEL') or os.getenv('ADAPTIX_MODEL')
            or os.getenv('OPENAI_MODEL') or '')


def env_budget(name, fallback):
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return fallback
    return parse_budget(str(raw).strip(), int)


def clean_log_line(line):
    text = _ANSI.sub('', str(line or '')).rstrip()
    if not text or any(marker in text for marker in _PROVIDER_NOISE):
        return ''
    return text


class Runner:
    """Owns one assessment run in a worker thread.

    The run is started as a subprocess of the same interpreter rather than a thread:
    ``main.main()`` installs signal handlers and calls ``argparse`` / ``SystemExit``,
    both of which are hostile inside a UI thread. A subprocess also means a cancel
    cannot corrupt the run, and the artifacts it writes are the shared state.
    """

    _interpreter_lock = threading.Lock()
    _interpreter_path = ''

    def __init__(self, view: LiveView):
        self.view = view
        self.process: subprocess.Popen | None = None
        self.thread: threading.Thread | None = None
        self.run_id = ''
        self.engine = 'adaptix'
        # Set by /resume. Empty means the next start begins a new run.
        self.resume_run_id = ''
        self.lock = threading.Lock()
        self.finished = threading.Event()
        self.finished.set()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @staticmethod
    def interpreter() -> str:
        """The interpreter that has this project's dependencies.

        ``sys.executable`` is only correct when the screen was started by the venv
        python. Started as ``/usr/bin/python -m src.adaptix.ui_entry`` it points at the
        system interpreter, and every run then dies on a missing ``litellm``. Prefer the
        venv beside the project root, and prove the full import works before using it.

        Importing litellm costs ~7s, so the probe result is cached for the life of the
        process and the web server warms it in the background at startup. The probe must
        stay a real import: ``find_spec`` only proves a path exists and would accept a
        module whose transitive imports are broken.
        """
        with Runner._interpreter_lock:
            if Runner._interpreter_path:
                return Runner._interpreter_path
            candidates = [sys.executable]
            for name in ('.venv/bin/python', 'venv/bin/python', '.venv/Scripts/python.exe'):
                candidates.append(os.path.abspath(name))
            for candidate in candidates:
                if not candidate or not os.path.exists(candidate):
                    continue
                try:
                    probe = subprocess.run([candidate, '-c', 'import litellm, langgraph'],
                                           capture_output=True, timeout=60, cwd=os.getcwd())
                except (OSError, subprocess.SubprocessError):
                    continue
                if probe.returncode == 0:
                    Runner._interpreter_path = candidate
                    return candidate
            return sys.executable

    @staticmethod
    def warm_interpreter():
        """Resolve the interpreter off the request thread while the operator reads the UI."""
        def probe():
            try:
                Runner.interpreter()
            except Exception:
                pass
        threading.Thread(target=probe, daemon=True, name='adaptix-interpreter-probe').start()

    def command(self, instruction: str) -> list[str]:
        view = self.view
        argv = [self.interpreter(), '-u', '-m', 'src.adaptix.main',
                '--instruction', instruction,
                '--run-id', self.run_id,
                '--model-context-tokens', str(view.context_tokens),
                '--time-budget', budget_argument(view.time_budget),
                '--tool-call-budget', budget_argument(view.tool_budget),
                '--token-budget', budget_argument(view.token_budget),
                '--max-iterations', str(view.max_iterations),
                '--planner-retries', '2',
                '--llm-timeout', '180']
        if self.resume_run_id:
            argv.extend(['--resume', self.resume_run_id])
        if any(value is None for value in (view.time_budget, view.tool_budget, view.token_budget)):
            argv.append('--confirm-unlimited-remote')
        for target in view.target:
            argv.extend(['--target', target])
        if view.identity:
            argv.extend(['--identity-context', view.identity])
        if view.model:
            argv.extend(['--model', view.model])
        extra = os.getenv('ADAPTIX_TUI_ARGS')
        if extra:
            import shlex
            argv.extend(shlex.split(extra))
        return argv

    def start(self, instruction: str, cwd: str):
        if self.engine == 'opencode':
            from src.adaptix.opencode_runner import start_opencode
            self.finished.clear()
            self.view.status = 'starting'
            self.view.run_id = ''
            start_opencode(self, instruction)
            return
        if self.resume_run_id:
            self.run_id = self.resume_run_id
        else:
            self.run_id = time.strftime('ui-%H%M%S')
        self.view.run_id = self.run_id
        self.view.objective = instruction
        self.view.status = 'starting'
        self.view.stop_reason = ''
        self.view.log = []
        self.view.started_at = time.time()
        self.view.append(f'objective: {instruction[:160]}')
        argv = self.command(instruction)
        self.view.append('exec: ' + ' '.join(argv[:6]) + ' ...')
        self.finished.clear()

        def work():
            env = dict(os.environ, PYTHONUNBUFFERED='1', COLUMNS='100')
            try:
                self.process = subprocess.Popen(argv, cwd=cwd, env=env,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT,
                                                text=True, bufsize=1)
                for line in self.process.stdout or []:
                    line = clean_log_line(line)
                    if (not line or line.startswith(('{', '}', '  ', '[EVENT]'))
                            or line.startswith('===') or line in ('[', ']')):
                        continue
                    self.view.append(line[:400])
                code = self.process.wait()
                self.view.append(f'run finished (exit {code})')
                self.poll_artifacts(cwd)
            except OSError as exc:
                self.view.append(f'could not start the run: {exc}')
            finally:
                self.finished.set()

        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()

    def cancel(self):
        if self.running:
            if self.engine == 'opencode':
                from src.adaptix.opencode_runner import kill_opencode
                kill_opencode(self)
            elif self.engine == 'code':
                from src.adaptix.code_audit.runner import kill_code
                kill_code(self)
            else:
                self.process.terminate()
            self.view.append('cancel requested')

    @staticmethod
    def _latest_json(base, pattern):
        paths = sorted(glob.glob(os.path.join(base, pattern)), key=os.path.getmtime)
        for path in reversed(paths):
            try:
                with open(path, encoding='utf-8') as handle:
                    value = json.load(handle)
            except (OSError, ValueError):
                continue
            if isinstance(value, dict):
                return value
        return None

    def _is_stale(self, base: str, progress: dict) -> bool:
        started = self.view.started_at or 0
        if not started:
            return False
        try:
            paths = glob.glob(os.path.join(base, 'progress-*.json'))
            if not paths:
                return False
            newest = max(paths, key=os.path.getmtime)
            return os.path.getmtime(newest) < started
        except OSError:
            return False

    def poll_artifacts(self, cwd: str):
        """Read the newest LangGraph progress, checkpoint and report into the view."""
        if self.engine == 'opencode':
            if self.view.started_at:
                self.view.elapsed = time.time() - self.view.started_at
            return self.view
        if self.engine == 'code':
            # code_audit.runner owns this view's progress/report polling.
            if self.view.started_at:
                self.view.elapsed = time.time() - self.view.started_at
            return self.view
        if not self.run_id:
            return
        base = os.path.join(cwd, 'artifacts', 'scans', self.run_id)
        progress = self._latest_json(base, 'progress-*.json')
        if progress and self._is_stale(base, progress):
            progress = None
        if progress:
            self.view = view_from_progress(progress, self.view)
        checkpoints = sorted(glob.glob(os.path.join(base, 'checkpoint-*.json')),
                             key=os.path.getmtime)
        merged = None
        if checkpoints:
            try:
                with open(checkpoints[-1], encoding='utf-8') as handle:
                    state = json.load(handle)
            except (OSError, ValueError):
                state = None
            if state:
                merged = view_from_state(state, self.view)
                merged.tokens = read_tokens(state)
                if not progress:
                    phases = [row for row in (state.get('phase_runtime') or []) if isinstance(row, dict)]
                    if phases:
                        merged.workflow_node = str(phases[-1].get('phase') or '')
                        merged.workflow_phase = 'completed'
                    if self.running:
                        merged.status = 'running'
        report = self._latest_json(base, 'report-*.json')
        if report:
            merged = view_from_report(report, merged or self.view)
        if merged is None:
            merged = self.view
            if self.running:
                merged.status = 'running' if progress else 'starting'
        if not self.running and merged.status in ('starting', 'recon', 'running'):
            merged.status = 'finishing'
        if self.view.started_at:
            merged.elapsed = time.time() - self.view.started_at
        self.view = merged
        return merged


def resumable_runs(cwd: str, limit: int = 8):
    """Run ids with a checkpoint that still has work to do, newest first.

    The checkpoint machinery is only imported when a run actually has a
    checkpoint file. Importing it eagerly built the whole LangGraph and cost ~17s
    on the first /api/flows request, which made every UI refresh after a restart
    look stuck before any flow was shown.
    """
    scans = os.path.join(cwd, 'artifacts', 'scans')
    try:
        names = sorted(os.listdir(scans), reverse=True)
    except OSError:
        return []
    candidates = [name for name in names
                  if not name.startswith('.')
                  and os.path.isfile(os.path.join(scans, name, 'checkpoint.sqlite'))]
    if not candidates:
        return []
    found = []
    try:
        sys.path.insert(0, cwd)
        from src.adaptix.evidence.checkpoint import pending_nodes
    except Exception:
        return []
    for name in candidates:
        try:
            if pending_nodes(name):
                found.append(name)
        except Exception:
            continue
        if len(found) >= limit:
            break
    return found
