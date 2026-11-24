"""Error analysis of the reviewer on the seeded PRs, from run artifacts only (no new runs).

For every review of a defective seeded PR, this reads the reviewer's transcript (downloaded by
collect_results.py into results/.cache), takes the probe scripts the reviewer wrote under scratch/,
and re-runs each probe the reviewer actually ran on two versions of the code:

* the seeded PR (pinned commit + seeded patch), and
* the correct reference fix of the same issue (pinned commit + hidden_tests/reference_fixes/<issue>.patch).

A probe *exposes* the planted defect when its result differs between the two (exit code, printed
output, last error line, or per-test outcomes for pytest probes). Each review is then classified:
caught; missed although a probe exposed the defect (the reviewer saw the evidence and approved);
missed because no probe exposed it; missed without any probe of its own.

Probe scripts that use subprocess, os.system, sockets, HTTP or recursive deletion are not executed and
are listed as skipped. Usage:

    python experiment/scripts/analyze_reviews.py --pinned "$WS/tinydb-pinned" --python "$WS/.venv-hidden/bin/python"
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EXPERIMENT, RESULTS, SEEDED  # noqa: E402

REFERENCE = EXPERIMENT / 'hidden_tests' / 'reference_fixes'
UNSAFE = re.compile(r'\bsubprocess\b|\bos\.system\b|\bos\.popen\b|\bsocket\b|\brequests\b|\burllib\b|'
                    r'\bhttp\.client\b|\bshutil\.rmtree\b|\b__import__\b|\bctypes\b|\bos\.exec')
CLASSES = ['caught, a probe exposed it', 'caught without an exposing probe',
           'missed: a probe exposed it, approved anyway', 'missed: probes never exposed it',
           'missed: no probe of its own', 'no verdict', 'no transcript']


def records(folder: Path) -> list[dict]:
    out = []
    for f in sorted((folder / 'transcripts').glob('*.jsonl')):
        for line in f.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def compare_outputs(recs: list[dict]) -> list[bool]:
    """For every compare.sh run in the transcript: did the two halves (PR head, before the change) differ?"""
    pending: list[dict] = []
    results: list[bool] = []
    for rec in recs:
        if rec.get('type') == 'assistant':
            pending = list(rec.get('tool_calls') or [])
        elif rec.get('type') == 'tool' and pending:
            call = pending.pop(0)
            args = call.get('arguments') or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            output = str(rec.get('output', ''))
            if call.get('name') == 'run_command' and 'compare.sh' in str(args.get('command', '')) \
                    and '=== before the change' in output:
                head, before = output.split('=== before the change', 1)
                head = head.split('=== PR head ===', 1)[-1]
                before = before.split('===', 1)[-1]
                results.append(head.strip() != before.strip())
    return results


def probes(recs: list[dict]) -> tuple[dict, list[str]]:
    """Probe files the reviewer wrote under scratch/ (last version wins) and every command it ran."""
    files: dict[str, str] = {}
    commands: list[str] = []
    for rec in recs:
        if rec.get('type') != 'assistant':
            continue
        for call in rec.get('tool_calls') or []:
            args = call.get('arguments') or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if call.get('name') == 'write_file':
                path = str(args.get('path', ''))
                if 'scratch/' in path and path.endswith('.py'):
                    rel = path.rsplit('scratch/', 1)[1]
                    if not rel.startswith('base/'):
                        files[rel] = str(args.get('content', ''))
            elif call.get('name') == 'run_command':
                commands.append(str(args.get('command', '')))
    return files, commands


def tree(pinned: Path, patch: Path, dest: Path) -> Path:
    if not dest.exists():
        shutil.copytree(pinned, dest, ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache'))
        env = {**os.environ, 'GIT_CEILING_DIRECTORIES': str(dest.parent)}   # never inside another repository
        proc = subprocess.run(['git', 'apply', '--verbose', str(patch)], cwd=dest, capture_output=True, text=True, env=env)
        if proc.returncode != 0 or 'Skipped patch' in proc.stderr:
            raise RuntimeError(f'{patch.name} did not apply cleanly: {proc.stderr[-300:]}')
    return dest


def signature(files: dict, name: str, code_dir: Path, python: str) -> tuple:
    """What a probe shows on one version of the code, with paths, addresses and timings removed."""
    for path in set(re.findall(r'''['"](/tmp/[\w./-]+)['"]''', files[name])):
        if os.path.isfile(path):
            os.remove(path)                       # no state carried over between versions
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for rel, content in files.items():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp / rel).write_text(content, encoding='utf-8')
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': tmp_name, 'TMPDIR': tmp_name,
               'PYTHONPATH': str(code_dir), 'SCRATCH': tmp_name, 'REPO': str(code_dir), 'BASE': str(code_dir),
               'PYTHONDONTWRITEBYTECODE': '1'}
        is_test = Path(name).name.startswith('test_') or re.search(r'^def test_', files[name], re.M)
        cmd = ([python, '-m', 'pytest', '-q', '--tb=no', '-rA', '-p', 'no:cacheprovider', '-o', 'addopts=',
                '--rootdir', tmp_name, str(tmp / name)] if is_test else [python, str(tmp / name)])
        try:
            proc = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return ('timeout',)

        def clean(text: str) -> str:
            text = text.replace(str(code_dir), '<CODE>').replace(tmp_name, '<TMP>')
            text = re.sub(r'0x[0-9a-fA-F]+', '0x?', text)
            return re.sub(r' in [0-9.]+s\b', ' in ?s', text)
        errors = [line for line in proc.stderr.splitlines() if line.strip()]
        return (proc.returncode, clean(proc.stdout).strip(), clean(errors[-1]) if errors else '')


def classify(verdict: str, ran: list, exposing: list) -> str:
    if verdict == 'request_changes':
        return CLASSES[0] if exposing else CLASSES[1]
    if verdict == 'approve':
        if exposing:
            return CLASSES[2]
        return CLASSES[3] if ran else CLASSES[4]
    return CLASSES[5]


def analyse(rows: list[dict], cache: Path, pinned: Path, python: str, work: Path) -> list[dict]:
    seeded = {p['id']: p for p in json.loads((SEEDED / 'seeded_prs.json').read_text())}
    out = []
    for r in rows:
        pr = seeded.get(r['seeded_id'])
        if not pr or pr['expected_verdict'] == 'approve':
            continue                                 # only defective PRs have a defect to expose
        folder = cache / str(r['run_id']) / 'review-r1'
        verdict = r['final_verdict'] or 'error'
        item = {'run_id': r['run_id'], 'run_url': r['run_url'], 'seeded_id': r['seeded_id'],
                'seeded_set': r.get('seeded_set') or 'dev', 'group': f"{r['variant']} · {r.get('campaign') or 'c1'}",
                'verdict': verdict, 'probes_written': 0, 'probes_run': 0, 'probes_exposing': 0,
                'probes_skipped_unsafe': 0, 'used_compare': False, 'exposing_probe': '', 'class': CLASSES[6],
                'compare_runs': 0, 'compare_showed_difference': 0}
        if not (folder / 'transcripts').is_dir():
            out.append(item)
            continue
        recs = records(folder)
        files, commands = probes(recs)
        compared = compare_outputs(recs)
        item.update(compare_runs=len(compared), compare_showed_difference=sum(compared))
        joined = '\n'.join(commands)
        ran = [n for n in files if Path(n).name in joined]
        head = tree(pinned, SEEDED / pr['patch'], work / f"{pr['id']}-head")
        ref = tree(pinned, REFERENCE / f"{pr['issue_key']}.patch", work / f"{pr['issue_key']}-reference")
        exposing, skipped = [], 0
        for name in ran:
            if UNSAFE.search(files[name]):
                skipped += 1
                continue
            if signature(files, name, head, python) != signature(files, name, ref, python):
                exposing.append(name)
        item.update(probes_written=len(files), probes_run=len(ran), probes_exposing=len(exposing),
                    probes_skipped_unsafe=skipped, used_compare='compare.sh' in joined,
                    exposing_probe=exposing[0] if exposing else '', **{'class': classify(verdict, ran, exposing)})
        out.append(item)
    return out


def write(items: list[dict], out: Path) -> None:
    fields = ['run_id', 'run_url', 'seeded_id', 'seeded_set', 'group', 'verdict', 'class', 'probes_written',
              'probes_run', 'probes_exposing', 'probes_skipped_unsafe', 'used_compare', 'exposing_probe',
              'compare_runs', 'compare_showed_difference']
    with open(out / 'review_analysis.csv', 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
    md = ['# Why the reviewer missed defects: error analysis of the seeded-PR reviews', '',
          '_Generated by `experiment/scripts/analyze_reviews.py` from the review artifacts (no new runs). '
          'Do not edit by hand._', '',
          'For each review of a **defective** seeded PR, every probe script the reviewer wrote and ran was re-run on '
          'the seeded PR and on the correct reference fix of the same issue. A probe *exposes* the defect when its '
          'result differs between the two. "Approved anyway" means the reviewer ran a probe whose output showed the '
          'defect and still approved; "probes never exposed it" means its probes did not touch the defect.', '']
    for set_name, title in (('dev', 'Dev set (S2, S3, S4)'), ('heldout', 'Held-out set (S7, S8, S9)')):
        subset = [i for i in items if i['seeded_set'] == set_name]
        if not subset:
            continue
        groups = sorted({i['group'] for i in subset})
        md += [f'## {title}', '', '| Outcome | ' + ' | '.join(groups) + ' |', '|---' * (len(groups) + 1) + '|']
        counts = {g: Counter(i['class'] for i in subset if i['group'] == g) for g in groups}
        for cls in CLASSES:
            if any(counts[g][cls] for g in groups):
                md.append(f'| {cls} | ' + ' | '.join(str(counts[g][cls]) for g in groups) + ' |')
        for label, key in (('mean probes run per review', 'probes_run'),):
            md.append(f'| {label} | ' + ' | '.join(
                f"{sum(i[key] for i in subset if i['group'] == g) / max(1, sum(1 for i in subset if i['group'] == g)):.1f}"
                for g in groups) + ' |')
        md.append('')
    compare_items = [i for i in items if i['compare_runs']]
    if compare_items:
        runs = sum(i['compare_runs'] for i in compare_items)
        diff = sum(i['compare_showed_difference'] for i in compare_items)
        md += ['## Did the before/after comparison work in the real runs?', '',
               f'{runs} `compare.sh` runs in {len(compare_items)} reviews; {diff} showed a difference between the PR '
               'head and the code before the change. On a PR that adds a function (S4, S7, S8), a probe that calls '
               'it must fail on the code before the change, so identical halves there would mean the pre-change '
               'code was not rebuilt.', '']
        feature = [i for i in compare_items if i['seeded_id'] in ('S4', 'S7', 'S8') and not i['compare_showed_difference']]
        md += [f'Reviews of S4/S7/S8 where no comparison showed any difference: {len(feature)} of '
               f"{len([i for i in compare_items if i['seeded_id'] in ('S4', 'S7', 'S8')])}.", '']
    md += ['## Every review of a defective seeded PR', '',
           '| Run | Seeded PR | Group | Verdict | Outcome | Probes run | Exposing | Skipped (unsafe) | compare.sh runs (differed) |',
           '|---|---|---|---|---|---|---|---|---|']
    md += [f"| [{i['run_id']}]({i['run_url']}) | {i['seeded_id']} | {i['group']} | {i['verdict']} | {i['class']} | "
           f"{i['probes_run']} | {i['probes_exposing']} | {i['probes_skipped_unsafe']} | {i['compare_runs']} ({i['compare_showed_difference']}) |"
           for i in items]
    (out / 'review_analysis.md').write_text('\n'.join(md) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pinned', required=True, type=Path, help='clean checkout at the pinned commit')
    ap.add_argument('--python', default=sys.executable, help='python of a venv with pytest')
    args = ap.parse_args()
    rows = [r for r in csv.DictReader(open(RESULTS / 'results.csv', encoding='utf-8'))
            if r.get('seeded_id') and r.get('mode') == 'review' and r.get('outcome') != 'provider quota']
    with tempfile.TemporaryDirectory() as work:
        items = analyse(rows, RESULTS / '.cache', args.pinned.resolve(), args.python, Path(work))
    write(items, RESULTS)
    print(f'wrote {RESULTS}/review_analysis.md and .csv ({len(items)} reviews of defective seeded PRs)')
    print(Counter(i['class'] for i in items))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
