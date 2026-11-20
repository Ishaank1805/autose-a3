"""Validate the five seeded reviewer-check PRs against the pinned base commit.

For each seeded PR this applies its patch to a clean checkout and records:

* whether the project's full test suite passes (a seeded *bad* PR is only an
  interesting reviewer check if CI is green, i.e. tests alone don't catch it);
* the hidden acceptance tests of the linked issue;
* whether the planted defect is really present, using the PR's ``probe``.

Usage:

    python experiment/scripts/validate_seeded_prs.py --repo /path/to/clean/checkout \
        --python /path/to/venv/bin/python
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hidden_runner import run_hidden, run_pytest, summarize  # noqa: E402

SEEDED = Path(__file__).resolve().parent.parent / 'seeded_prs'


def git(repo: Path, *args: str) -> None:
    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True)


def probe(repo: Path, python: str, code: str) -> bool:
    script = code + '\nprint("DEFECT_PRESENT=%s" % DEFECT_PRESENT)\n'
    out = subprocess.run([python, '-c', script], cwd=repo, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f'probe failed:\n{out.stderr}')
    return 'DEFECT_PRESENT=True' in out.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True, type=Path)
    ap.add_argument('--python', default=sys.executable)
    args = ap.parse_args()
    repo = args.repo.resolve()
    prs = json.loads((SEEDED / 'seeded_prs.json').read_text())

    ok = True
    for pr in prs:
        git(repo, 'apply', str(SEEDED / pr['patch']))
        try:
            suite = run_pytest(repo, args.python, [])
            hidden = run_hidden(repo, pr['issue_key'], args.python)
            defect = probe(repo, args.python, pr['probe'])
        finally:
            git(repo, 'checkout', '--', '.')
            git(repo, 'clean', '-fdq')
        h_pass, h_total = summarize(hidden['outcomes'])
        s_pass, s_total = summarize(suite['outcomes'])
        expect_defect = pr['expected_verdict'] != 'approve'
        good = suite['returncode'] == 0 and defect == expect_defect
        ok &= good
        print(f"[{'OK ' if good else 'BAD'}] {pr['id']} ({pr['expected_verdict']:15s}) "
              f"suite {s_pass}/{s_total} | hidden {h_pass}/{h_total} | defect present: {defect}")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
