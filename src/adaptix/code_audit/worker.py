"""Subprocess entry point for one static code audit.

Kept out of the Flask process so a cancel or a provider stall cannot block the UI,
and so the worker inherits the same interpreter/dependency environment as the
existing CLI runs.
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from src.adaptix.code_audit.engine import run_audit
from src.adaptix.code_audit.sources import load_bundle
from src.adaptix.config import ROOT, load_dotenv

BUDGET_KEYS = ('time_budget', 'token_budget', 'max_iterations')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='ADAPTIX static code audit worker')
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--instruction', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--time-budget', type=int, default=900)
    parser.add_argument('--token-budget', type=int, default=50000)
    parser.add_argument('--max-iterations', type=int, default=8)
    parser.add_argument('--api-base', default=None)
    parser.add_argument('--api-key', default=None)
    return parser.parse_args(argv)


def main(argv=None):
    load_dotenv()
    args = parse_args(argv)
    run_dir = Path(args.run_dir)
    try:
        bundle = load_bundle(run_dir)
        state = run_audit(
            run_dir, args.instruction, model=args.model, bundle=bundle,
            time_budget=args.time_budget, token_budget=args.token_budget,
            max_iterations=args.max_iterations,
            api_base=args.api_base or os.getenv('ADAPTIX_API_BASE') or None,
            api_key=args.api_key or os.getenv('ADAPTIX_API_KEY') or None,
        )
    except Exception as exc:
        traceback.print_exc()
        from src.adaptix.code_audit.engine import _progress
        _progress(run_dir, {'status': 'completed_with_errors',
                            'stop_reason': 'worker_error',
                            'error': f'{type(exc).__name__}: {exc}'[:500],
                            'model': args.model})
        return 2
    return 0 if state.get('status') == 'completed' and state.get('report') else 2


if __name__ == '__main__':
    raise SystemExit(main())
