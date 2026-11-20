"""Shared helpers for the experiment scripts. They use the GitHub CLI, authenticated as you."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent
ISSUES = EXPERIMENT / 'issues'
SEEDED = EXPERIMENT / 'seeded_prs'
RESULTS = ROOT / 'results'


def gh(*args: str, input: str | None = None, check: bool = True) -> str:
    proc = subprocess.run(['gh', *args], input=input, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:3])} failed: {proc.stderr.strip()}")
    return proc.stdout


def gh_json(*args: str):
    return json.loads(gh(*args) or 'null')


def guard(repo: str) -> None:
    if repo.lower().startswith('msiemens/'):
        raise SystemExit('Refusing to act on the upstream repository; pass your fork, e.g. you/tinydb.')


def read_issue(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if not match:
        raise SystemExit(f'{path}: missing front matter')
    meta: dict = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(':')
        value = value.strip()
        meta[key.strip()] = ([v.strip() for v in value.strip('[]').split(',') if v.strip()]
                             if value.startswith('[') else value.strip('"'))
    return meta, match.group(2).strip() + '\n'
