"""Validate the hidden acceptance tests against the pinned base commit.

For every issue this checks three things in a scratch checkout:

1. on the base commit, at least one hidden test fails (the tests really
   exercise the requested change);
2. with the reference fix applied, every hidden test passes;
3. with the reference fix applied, the project's full test suite still passes.

Usage (from the submission repo root):

    python experiment/scripts/validate_hidden_tests.py --repo /path/to/fork/checkout

The checkout must be clean and at the pinned base commit; it is restored
with ``git checkout -- . && git clean -fd`` after each issue.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hidden_runner import HIDDEN_DIR, run_hidden, run_pytest, summarize  # noqa: E402

ISSUES = ['issue_1', 'issue_2', 'issue_3', 'issue_4', 'issue_5']


def git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True, type=Path, help='clean checkout of the fork at the base commit')
    ap.add_argument('--python', default=sys.executable, help='python of a venv where the repo is installed (-e)')
    ap.add_argument('--json', type=Path, help='optional path for a JSON report')
    args = ap.parse_args()
    repo = args.repo.resolve()

    if git(repo, 'status', '--porcelain').strip():
        print(f'{repo} is not clean; refusing to touch it', file=sys.stderr)
        return 2

    report, ok = {}, True
    for key in ISSUES:
        base = run_hidden(repo, key, args.python)
        patch = HIDDEN_DIR / 'reference_fixes' / f'{key}.patch'
        git(repo, 'apply', str(patch))
        try:
            fixed = run_hidden(repo, key, args.python)
            suite = run_pytest(repo, args.python, [])
        finally:
            git(repo, 'checkout', '--', '.')
            git(repo, 'clean', '-fdq')
        b_pass, b_total = summarize(base['outcomes'])
        f_pass, f_total = summarize(fixed['outcomes'])
        s_pass, s_total = summarize(suite['outcomes'])
        checks = {
            'fails_on_base': b_pass < b_total,
            'passes_with_reference_fix': f_total > 0 and f_pass == f_total,
            'full_suite_green_with_fix': suite['returncode'] == 0,
        }
        ok &= all(checks.values())
        report[key] = {'base': base['outcomes'], 'fixed': fixed['outcomes'],
                       'suite': f'{s_pass}/{s_total}', **checks}
        flag = 'OK ' if all(checks.values()) else 'BAD'
        print(f'[{flag}] {key}: base {b_pass}/{b_total} pass | reference fix {f_pass}/{f_total} pass | '
              f'full suite {s_pass}/{s_total}')
        for name, outcome in base['outcomes'].items():
            print(f'        base  {outcome:7s} {name}')

    if args.json:
        args.json.write_text(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
