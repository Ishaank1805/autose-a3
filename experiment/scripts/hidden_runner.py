"""Run the hidden acceptance tests of one issue against a checkout of the fork.

The hidden tests live in ``experiment/hidden_tests/issue_<k>/`` of the
submission repository, i.e. outside the repository the agents work on. To
run them we copy the test file into the checkout's ``tests/`` directory under
a throw-away name, run pytest on that single file, read the JUnit XML report
and delete the copy again. The checkout itself is never committed to.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN_DIR = HERE.parent / 'hidden_tests'


def hidden_test_file(issue_key: str) -> Path:
    """Return the hidden test file for ``issue_key`` (e.g. ``issue_3``)."""
    files = sorted((HIDDEN_DIR / issue_key).glob('test_*.py'))
    if len(files) != 1:
        raise FileNotFoundError(f'expected exactly one test file in {HIDDEN_DIR / issue_key}')
    return files[0]


def run_pytest(repo: Path, python: str, targets: list[str], timeout: int = 600) -> dict:
    """Run pytest in ``repo`` and return ``{'outcomes': {name: outcome}, 'returncode': int, 'output': str}``."""
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / 'junit.xml'
        cmd = [python, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts=',
               f'--junitxml={junit}', *targets]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=timeout, env=env)
        outcomes: dict[str, str] = {}
        if junit.exists():
            for case in ET.parse(junit).getroot().iter('testcase'):
                # classname keeps same-named tests in different modules apart
                name = case.get('name', '?')
                if len(targets) != 1:
                    name = f"{case.get('classname', '')}::{name}"

                if case.find('failure') is not None:
                    outcome = 'failed'
                elif case.find('error') is not None:
                    outcome = 'error'
                elif case.find('skipped') is not None:
                    outcome = 'skipped'
                else:
                    outcome = 'passed'
                outcomes[name] = outcome
        return {'outcomes': outcomes, 'returncode': proc.returncode,
                'output': (proc.stdout + proc.stderr)[-4000:]}


def run_hidden(repo: Path, issue_key: str, python: str = sys.executable) -> dict:
    """Copy the hidden tests of ``issue_key`` into ``repo/tests``, run them and clean up."""
    src = hidden_test_file(issue_key)
    dest = Path(repo) / 'tests' / f'_hidden_{src.name}'
    shutil.copyfile(src, dest)
    try:
        return run_pytest(Path(repo), python, [str(dest.relative_to(repo))])
    finally:
        dest.unlink(missing_ok=True)


def summarize(outcomes: dict[str, str]) -> tuple[int, int]:
    """Return ``(passed, total)``."""
    return sum(1 for o in outcomes.values() if o == 'passed'), len(outcomes)
