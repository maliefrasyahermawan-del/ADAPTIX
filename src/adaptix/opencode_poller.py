"""Per-run bridge between an ADAPTIX external run and opencode-pentester's SQLite state.

Runs inside WSL (the engine lives there). It never writes to the pentester database:
it only reads session_log/vulns/leads and the deterministic completion gate, then
publishes small JSON/NDJSON snapshots the Windows ADAPTIX runner can tail.
"""
import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path


def atomic_write(path: Path, payload):
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding='utf-8')
    tmp.replace(path)


def append_jsonl(path: Path, row):
    with path.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')


def connect(db_path: Path):
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=2)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace')
    parser.add_argument('engagement')
    parser.add_argument('skill_dir')
    parser.add_argument('--interval', type=float, default=1.0)
    args = parser.parse_args()

    ws = Path(args.workspace)
    db_path = Path(os.environ.get('PENTEST_DB') or (ws / 'db' / 'findings.db'))
    skill_dir = Path(args.skill_dir)
    out_dir = ws / 'state'
    out_dir.mkdir(parents=True, exist_ok=True)
    activity_path = ws / 'activity.ndjson'
    findings_path = ws / 'findings.ndjson'
    state_path = out_dir / 'state.json'
    gate_path = out_dir / 'gate.json'
    stop_path = ws / 'stop-poller'

    last_log = 0
    last_vuln = 0
    last_gate_at = 0.0
    gate_result = None
    stopping = {'value': False}

    def stop(_signum, _frame):
        stopping['value'] = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while not stopping['value'] and not stop_path.exists():
        try:
            if not db_path.is_file():
                atomic_write(state_path, {'updated_at': time.time(), 'state': 'starting',
                                          'engagement': args.engagement,
                                          'counts': {}, 'gate': None})
                time.sleep(args.interval)
                continue
            conn = connect(db_path)
            conn.row_factory = sqlite3.Row
            engagement = conn.execute(
                'SELECT id, state, status, target, scope FROM engagements WHERE id=?',
                (args.engagement,)).fetchone()
            if engagement is None:
                conn.close()
                time.sleep(args.interval)
                continue
            eng_id = engagement['id']
            logs = conn.execute(
                'SELECT id, created_at, agent, action, summary, phase, tool, command, target, '
                'exit_code, duration_ms, output_file, output_hash, output_excerpt '
                'FROM session_log WHERE engagement_id=? AND id>? ORDER BY id',
                (eng_id, last_log)).fetchall()
            for row in logs:
                append_jsonl(activity_path, dict(row))
                last_log = max(last_log, int(row['id']))
            vulns = conn.execute(
                'SELECT id, title, severity, status, tool_used, cve, description, evidence_file, '
                'poc_output, created_at FROM vulns WHERE engagement_id=? AND id>? ORDER BY id',
                (eng_id, last_vuln)).fetchall()
            for row in vulns:
                append_jsonl(findings_path, dict(row))
                last_vuln = max(last_vuln, int(row['id']))
            counts = {
                'hosts': conn.execute('SELECT COUNT(*) FROM hosts WHERE engagement_id=?', (eng_id,)).fetchone()[0],
                'services': conn.execute(
                    'SELECT COUNT(*) FROM services s JOIN hosts h ON h.id=s.host_id '
                    'WHERE h.engagement_id=?', (eng_id,)).fetchone()[0],
                'vulns': conn.execute('SELECT COUNT(*) FROM vulns WHERE engagement_id=?', (eng_id,)).fetchone()[0],
                'confirmed': conn.execute(
                    "SELECT COUNT(*) FROM vulns WHERE engagement_id=? AND status='confirmed'", (eng_id,)).fetchone()[0],
                'leads_open': conn.execute(
                    "SELECT COUNT(*) FROM leads WHERE engagement_id=? AND status='open'", (eng_id,)).fetchone()[0],
                'leads_total': conn.execute('SELECT COUNT(*) FROM leads WHERE engagement_id=?', (eng_id,)).fetchone()[0],
                'commands': conn.execute('SELECT COUNT(*) FROM session_log WHERE engagement_id=?', (eng_id,)).fetchone()[0],
                'chains': conn.execute('SELECT COUNT(*) FROM attack_chains WHERE engagement_id=?', (eng_id,)).fetchone()[0],
            }
            severity = {}
            for row in conn.execute(
                    "SELECT severity, COUNT(*) AS n FROM vulns WHERE engagement_id=? GROUP BY severity",
                    (eng_id,)):
                severity[row['severity']] = row['n']
            last_activity = dict(logs[-1]) if logs else None
            conn.close()

            now = time.time()
            if now - last_gate_at >= 5:
                last_gate_at = now
                try:
                    env = dict(os.environ)
                    env['PENTEST_DB'] = str(db_path)
                    env['PENTEST_ENGAGEMENT'] = eng_id
                    env['PENTEST_OUTPUTS'] = str(ws / 'outputs')
                    proc = subprocess.run(
                        ['bash', str(skill_dir / 'db' / 'findings.sh'), 'gate', '--json', '--no-record'],
                        capture_output=True, text=True, timeout=25, env=env, cwd=str(ws))
                    if proc.returncode in (0, 2) and proc.stdout.strip():
                        gate_result = json.loads(proc.stdout)
                        atomic_write(gate_path, gate_result)
                except (OSError, ValueError, subprocess.SubprocessError):
                    pass

            atomic_write(state_path, {
                'updated_at': now,
                'engagement': eng_id,
                'state': engagement['state'],
                'status': engagement['status'],
                'target': engagement['target'],
                'scope': engagement['scope'],
                'counts': counts,
                'severity': severity,
                'last_activity': last_activity,
                'gate': gate_result,
            })
        except (OSError, sqlite3.Error, ValueError):
            pass
        time.sleep(args.interval)

    try:
        atomic_write(state_path, {
            'updated_at': time.time(), 'engagement': args.engagement,
            'state': 'stopped', 'status': 'stopped', 'counts': {}, 'gate': gate_result,
        })
    except OSError:
        pass


if __name__ == '__main__':
    main()
