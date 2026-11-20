"""Autopilot: run the complete AutoSE experiment protocol in your fork with nobody in the loop.

    python experiment/scripts/autopilot.py doctor --repo YOU/tinydb
    python experiment/scripts/autopilot.py run --repo YOU/tinydb \
        --experiments single-agent,reviewer-sees-rationale --repeats 1 \
        --max-usd 60 --max-tokens 60000000 [--max-items N] [--retry-errors]

`run` works through a fixed plan, one run at a time: the five issues and the five
seeded PRs in the baseline, then the same targets for every experiment variant
(variants named reviewer-* run on the seeded PRs, all others on the issues),
repeated --repeats times. For each item it triggers the run the way a maintainer
would (label or comment), waits for it and records it in results/autopilot_log.json
whatever the outcome; a run that a stage stopped is a valid result. It is
resumable: run it again and it continues where it left off, including waiting
for a run that is still in progress. A run whose workflow failed (a red job) is
retried once automatically.

Exit codes: 0 plan complete; 3 a run failed twice or never appeared (investigate,
fix, then rerun with --retry-errors); 4 cost or token cap reached; 5 timed out
waiting for a run; 6 stopped after --max-items; 7 the model provider's daily quota is used up (run again after it
resets; the interrupted item is re-run).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

DONE, ERROR, BUDGET, TIMEOUT, PAUSED, QUOTA = 0, 3, 4, 5, 6, 7


def quota_stop(summary: dict) -> bool:
    text = str(summary.get('stop_reason', '')) + ' ' + ' '.join(str(r.get('error', '')) for r in summary.get('reviews') or [])
    return 'daily request quota' in text
ISSUE_KEYS = [f'issue_{i}' for i in range(1, 6)]
SEEDED_KEYS = [f'S{i}' for i in range(1, 6)]


class GH:
    def __init__(self, repo: str):
        self.repo = repo

    def run(self, *args: str) -> str:
        for attempt in range(4):
            proc = subprocess.run(['gh', *args], capture_output=True, text=True)
            if proc.returncode == 0:
                return proc.stdout
            if attempt < 3 and any(err in proc.stderr.lower() for err in ['network is unreachable', 'connection reset', 'timeout', 'handshake']):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"gh {' '.join(args[:3])} failed: {proc.stderr.strip()[:400]}")

    def json(self, *args: str) -> Any:
        return json.loads(self.run(*args) or 'null')


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def log_path() -> Path:
    return common.RESULTS / 'autopilot_log.json'


def save(log: dict) -> None:
    log_path().parent.mkdir(parents=True, exist_ok=True)
    log_path().write_text(json.dumps(log, indent=2) + '\n')


def plan(experiments: list[str], repeats: int, review_repeats: int = 0, redteam: bool = False) -> list[dict]:
    """Order matters when time or money runs out: every prefix of the plan contains complete
    baseline/variant pairs. Smoke run first, then the cheap reviewer experiment, then full runs."""
    review_repeats = review_repeats or repeats
    full_variants = ['baseline'] + [v for v in experiments if not v.startswith('reviewer-')]
    review_variants = ['baseline'] + [v for v in experiments if v.startswith('reviewer-')]
    items: list[dict] = []

    def add(kind: str, key: str, variant: str, rep: int) -> None:
        item = {'id': f'{kind}:{key}:{variant}:{rep}', 'kind': kind, 'key': key, 'variant': variant, 'rep': rep}
        if item['id'] not in {i['id'] for i in items}:
            items.append(item)

    add('full', ISSUE_KEYS[0], 'baseline', 1)                         # smoke test of the whole pipeline
    for rep in range(1, review_repeats + 1):
        for key in SEEDED_KEYS:
            for variant in review_variants:
                add('review', key, variant, rep)
    for rep in range(1, repeats + 1):
        for key in ISSUE_KEYS:
            for variant in full_variants:
                add('full', key, variant, rep)
    if redteam:
        add('full', 'redteam_1', 'baseline', 1)                       # prompt-injection evidence (ADR-009)
    return items


def trigger(gh: GH, item: dict, issues: dict, seeded: dict) -> tuple[int, str]:
    suffix = '' if item['variant'] == 'baseline' else f" variant={item['variant']}"
    if item['kind'] == 'full':
        number = int(issues[item['key']]['number'])
        labels = (gh.json('issue', 'view', str(number), '--repo', gh.repo, '--json', 'labels') or {}).get('labels', [])
        if item['variant'] == 'baseline' and not any(lbl.get('name') == 'autose' for lbl in labels):
            gh.run('issue', 'edit', str(number), '--repo', gh.repo, '--add-label', 'autose')
            return number, 'label "autose"'
        gh.run('issue', 'comment', str(number), '--repo', gh.repo, '--body', '/autose' + suffix)
        return number, '/autose' + suffix
    pr = seeded[item['key']]
    body = f"/autose review #{pr['issue']}" + suffix
    gh.run('pr', 'comment', str(pr['number']), '--repo', gh.repo, '--body', body)
    return int(pr['number']), body


def find_run(gh: GH, workflow: str, match: Callable[[dict], bool], since: str, known: set,
             timeout: int, sleep: Callable[[float], None]) -> dict | None:
    for _ in range(max(1, timeout // 15)):
        runs = gh.json('run', 'list', '--repo', gh.repo, '--workflow', workflow, '--limit', '30',
                       '--json', 'databaseId,createdAt,displayTitle,status,url') or []
        for run in sorted(runs, key=lambda r: r['createdAt']):
            if run['databaseId'] not in known and run['createdAt'] >= since and match(run):
                return run
        sleep(15)
    return None


def wait_run(gh: GH, run_id: int, timeout: int, sleep: Callable[[float], None]) -> dict | None:
    for _ in range(max(1, timeout // 30)):
        info = gh.json('run', 'view', str(run_id), '--repo', gh.repo, '--json', 'status,conclusion,url')
        if info and info.get('status') == 'completed':
            return info
        sleep(30)
    return None


def run_summary(gh: GH, run_id: int) -> dict | None:
    dest = common.RESULTS / '.cache' / str(run_id) / 'summary'
    if not (dest / 'run_summary.json').exists():
        dest.mkdir(parents=True, exist_ok=True)
        try:
            gh.run('run', 'download', str(run_id), '--repo', gh.repo, '--name', 'autose-run-summary', '--dir', str(dest))
        except RuntimeError:
            return None
    path = dest / 'run_summary.json'
    return json.loads(path.read_text()) if path.exists() else None


def totals(log: dict) -> tuple[float, int]:
    usd, tokens = 0.0, 0
    for entry in log['items'].values():
        for attempt in entry['attempts']:
            usd += float(attempt.get('usd') or 0)
            tokens += int(attempt.get('tokens') or 0)
    return round(usd, 2), tokens


def run_plan(gh: GH, args: argparse.Namespace, sleep: Callable[[float], None] = time.sleep) -> int:
    issues = json.loads((common.ISSUES / 'index.json').read_text())
    seeded = json.loads((common.SEEDED / 'index.json').read_text())
    log = json.loads(log_path().read_text()) if log_path().exists() else {'repo': gh.repo, 'items': {}, 'doctor': []}
    experiments = [v.strip() for v in args.experiments.split(',') if v.strip() and v.strip() != 'baseline']
    log['settings'] = {'experiments': experiments, 'repeats': args.repeats, 'review_repeats': args.review_repeats,
                       'redteam': args.redteam, 'max_usd': args.max_usd, 'max_tokens': args.max_tokens}
    items = plan(experiments, args.repeats, args.review_repeats, args.redteam)
    skipped = [i['id'] for i in items if i['key'] not in (issues if i['kind'] == 'full' else seeded)]
    if skipped:
        print('not opened, skipped: ' + ', '.join(skipped), flush=True)
    items = [i for i in items if i['id'] not in skipped]
    for item in items:
        log['items'].setdefault(item['id'], {**item, 'status': 'pending', 'attempts': [], 'allowance': 1 + args.retries})
    if args.retry_errors:
        for entry in log['items'].values():
            if entry['status'] == 'error':
                entry['status'] = 'pending'
                entry['allowance'] = len(entry['attempts']) + 1 + args.retries
    save(log)
    known = {a['run_id'] for e in log['items'].values() for a in e['attempts'] if a.get('run_id')}
    processed = 0
    for item in items:
        entry = log['items'][item['id']]
        while entry['status'] != 'done':
            if entry['status'] == 'error':
                last = entry['attempts'][-1] if entry['attempts'] else {}
                print(f"ERROR {item['id']}: {last.get('note') or last.get('conclusion')} {last.get('url', '')}", flush=True)
                save(log)
                return ERROR
            last = entry['attempts'][-1] if entry['attempts'] else None
            if entry['status'] == 'running' and last and not last.get('run_id'):      # interrupted after triggering
                run = find_run(gh, 'autose.yml', lambda r, n=last['number']: f'#{n} (' in (r.get('displayTitle') or ''),
                               last['since'], known, 300, sleep)
                if run:
                    last.update(run_id=run['databaseId'], url=run['url'])
                    known.add(run['databaseId'])
                else:
                    last['note'], entry['status'] = 'run never appeared', 'pending'
                save(log)
                continue
            if not (entry['status'] == 'running' and last and last.get('run_id') and not last.get('conclusion')):
                usd, tokens = totals(log)
                if usd >= args.max_usd or tokens >= args.max_tokens:
                    print(f'BUDGET cap reached: ~${usd} / {tokens:,} tokens', flush=True)
                    save(log)
                    return BUDGET
                if args.max_items and processed >= args.max_items:
                    save(log)
                    return PAUSED
                since = iso(utcnow() - timedelta(seconds=120))
                number, how = trigger(gh, item, issues, seeded)
                last = {'trigger': how, 'number': number, 'since': since, 'triggered_at': iso(utcnow())}
                entry['attempts'].append(last)
                entry['status'] = 'running'
                save(log)
                run = find_run(gh, 'autose.yml', lambda r, n=number: f'#{n} (' in (r.get('displayTitle') or ''),
                               since, known, 600, sleep)
                if run is None:
                    last['note'], entry['status'] = 'no workflow run appeared within 10 minutes', 'error'
                    continue
                last.update(run_id=run['databaseId'], url=run['url'])
                known.add(run['databaseId'])
                save(log)
                print(f"started {item['id']} via {how}: {run['url']}", flush=True)
            info = wait_run(gh, last['run_id'], args.run_timeout_minutes * 60, sleep)
            if info is None:
                save(log)
                return TIMEOUT
            last.update(conclusion=info.get('conclusion'), finished_at=iso(utcnow()))
            summary = run_summary(gh, last['run_id'])
            if summary:
                last.update(outcome=summary.get('outcome'), pr=summary.get('pr'),
                            tokens=int((summary.get('tokens') or {}).get('total') or 0),
                            usd=float(summary.get('est_cost_usd') or 0))
            processed += 1
            if summary and quota_stop(summary):
                last['note'] = "stopped by the provider's daily quota; re-run after the reset"
                entry['status'] = 'pending'
                entry['allowance'] = entry.get('allowance', 1) + 1
                save(log)
                print(f"QUOTA {item['id']}: the provider's daily quota is used up ({last['url']}); "
                      'run autopilot again after midnight Pacific time', flush=True)
                return QUOTA
            if info.get('conclusion') == 'success' and summary:
                entry['status'] = 'done'
                print(f"done {item['id']}: {last.get('outcome')} ({last['url']})", flush=True)
            elif len(entry['attempts']) < entry['allowance']:
                entry['status'] = 'pending'
                print(f"retry {item['id']}: run ended {info.get('conclusion')} ({last['url']})", flush=True)
            else:
                last['note'], entry['status'] = f"workflow concluded {info.get('conclusion')}", 'error'
            save(log)
    usd, tokens = totals(log)
    print(f'plan complete: {len(items)} items, ~${usd}, {tokens:,} tokens', flush=True)
    return DONE


def doctor(gh: GH, sleep: Callable[[float], None] = time.sleep) -> int:
    since = iso(utcnow() - timedelta(seconds=120))
    gh.run('workflow', 'run', 'autose-doctor.yml', '--repo', gh.repo, '--ref', 'main')
    run = find_run(gh, 'autose-doctor.yml', lambda r: True, since, set(), 600, sleep)
    if run is None:
        print('the doctor run never appeared (are workflows enabled in the fork?)', flush=True)
        return ERROR
    info = wait_run(gh, run['databaseId'], 1800, sleep) or {}
    log = json.loads(log_path().read_text()) if log_path().exists() else {'repo': gh.repo, 'items': {}, 'doctor': []}
    log.setdefault('doctor', []).append({'run_id': run['databaseId'], 'url': run['url'],
                                         'conclusion': info.get('conclusion'), 'at': iso(utcnow())})
    save(log)
    print(f"doctor {info.get('conclusion')}: {run['url']}", flush=True)
    return DONE if info.get('conclusion') == 'success' else ERROR


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('doctor')
    d.add_argument('--repo', required=True)
    r = sub.add_parser('run')
    r.add_argument('--repo', required=True)
    r.add_argument('--experiments', default='single-agent,reviewer-sees-rationale')
    r.add_argument('--repeats', type=int, default=1)
    r.add_argument('--review-repeats', type=int, default=0, help='repeats of the seeded-PR reviews (default: --repeats)')
    r.add_argument('--redteam', action='store_true', help='also run the red-team issue (needs open_issues --include-redteam)')
    r.add_argument('--max-usd', type=float, default=60.0)
    r.add_argument('--max-tokens', type=int, default=60_000_000)
    r.add_argument('--max-items', type=int, default=0)
    r.add_argument('--retries', type=int, default=1)
    r.add_argument('--retry-errors', action='store_true')
    r.add_argument('--run-timeout-minutes', type=int, default=240)
    args = ap.parse_args(argv)
    common.guard(args.repo)
    gh = GH(args.repo)
    return doctor(gh) if args.cmd == 'doctor' else run_plan(gh, args)


if __name__ == '__main__':
    raise SystemExit(main())
