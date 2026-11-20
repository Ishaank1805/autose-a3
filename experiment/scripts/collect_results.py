"""Collect every AutoSE run of your fork into results/ (results.csv, runs.md, summary.md).

All numbers come from real runs: the `autose-run-summary` and `autose-review-r*`
artifacts of each run, and the hidden tests re-run against the exact head
commit each run produced. Do not edit the generated files by hand.

    python experiment/scripts/collect_results.py --repo YOU/tinydb --clone ../tinydb-fork \
        --python ../hidden-venv/bin/python
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ISSUES, RESULTS, SEEDED, gh_json, guard  # noqa: E402
from hidden_runner import hidden_test_file, run_hidden, summarize  # noqa: E402

STAGES = ['requirements', 'design', 'implementation', 'testing', 'release']
FIELDS = ['run_id', 'run_url', 'created_at', 'mode', 'variant', 'issue_key', 'issue', 'kind', 'pr', 'pr_url',
          'head_sha', 'outcome', 'stopped_stage', *STAGES, 'review_rounds', 'review_verdicts', 'final_verdict',
          'seeded_id', 'expected_verdict', 'reviewer_correct', 'hidden_passed', 'hidden_total', 'checks_failed',
          'loops', 'tokens_input', 'tokens_output', 'tokens_cache_read', 'tokens_cache_write', 'tokens_total',
          'est_cost_usd', 'review_urls', 'ci_urls']


def download(repo: str, run_id: int, name: str, dest: Path) -> Path | None:
    if not dest.exists() or not any(dest.iterdir()):
        dest.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(['gh', 'run', 'download', str(run_id), '--repo', repo, '--name', name,
                               '--dir', str(dest)], capture_output=True, text=True)
        if proc.returncode != 0:
            return None
    return dest


def hidden_for(clone: Path, sha: str, issue_key: str, python: str) -> dict:
    subprocess.run(['git', '-C', str(clone), 'fetch', '-q', 'origin', sha], capture_output=True)
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / 'tree'
        added = subprocess.run(['git', '-C', str(clone), 'worktree', 'add', '-q', '--detach', str(tree), sha],
                               capture_output=True, text=True)
        if added.returncode:
            return {'error': added.stderr.strip()[:200]}
        try:
            result = run_hidden(tree, issue_key, python)
        finally:
            subprocess.run(['git', '-C', str(clone), 'worktree', 'remove', '--force', str(tree)], capture_output=True)
    passed, total = summarize(result['outcomes'])
    return {'passed': passed, 'total': total}


def hidden_count(issue_key: str) -> int:
    try:
        return len(re.findall(r'(?m)^def test_', hidden_test_file(issue_key).read_text()))
    except FileNotFoundError:
        return 0


def build_row(run: dict, summary: dict, reviews: list[dict], issues: dict, seeded: dict) -> dict:
    by_number = {v['number']: k for k, v in issues.items()}
    issue = int(summary['issue']) if str(summary.get('issue') or '').isdigit() else None
    key = by_number.get(issue, '')
    rounds: dict = {}
    for artifact in sorted(summary.get('progress') or {}):
        rounds.update(summary['progress'][artifact] or {})
    r0 = rounds.get('r0') or {}
    tokens = summary.get('tokens') or {}
    verdicts = [r.get('verdict') for r in reviews]
    by_role: dict = defaultdict(lambda: defaultdict(int))
    for job in (summary.get('usage_by_job') or {}).values():
        for role, slot in (job.get('by_role') or {}).items():
            for k in ('calls', 'input', 'output', 'cache_read', 'cache_write'):
                by_role[role][k] += int(slot.get(k, 0))
    row = {'run_id': run['databaseId'], 'run_url': run['url'], 'created_at': run['createdAt'],
           'mode': summary.get('mode'), 'variant': summary.get('variant'), 'issue_key': key, 'issue': issue,
           'kind': (issues.get(key) or {}).get('kind', ''), 'pr': summary.get('pr'), 'pr_url': summary.get('pr_url'),
           'head_sha': summary.get('head_sha', ''), 'outcome': summary.get('outcome'),
           'stopped_stage': summary.get('stopped_stage', ''),
           **{stage: (r0.get(stage) or {}).get('status', 'not reached') for stage in STAGES},
           'review_rounds': len(reviews), 'review_verdicts': ' > '.join(v or '?' for v in verdicts),
           'final_verdict': verdicts[-1] if verdicts else '',
           'seeded_id': '', 'expected_verdict': '', 'reviewer_correct': '', 'hidden_passed': '', 'hidden_total': '',
           'checks_failed': sum(v.get('failed', 0) for v in (summary.get('check_stats') or {}).values()),
           'loops': len(summary.get('loops') or []),
           'tokens_input': tokens.get('input', 0), 'tokens_output': tokens.get('output', 0),
           'tokens_cache_read': tokens.get('cache_read', 0), 'tokens_cache_write': tokens.get('cache_write', 0),
           'tokens_total': tokens.get('total', 0), 'est_cost_usd': summary.get('est_cost_usd', 0),
           'review_urls': ' '.join(r.get('review_url', '') for r in reviews if r.get('review_url')),
           'ci_urls': ' '.join(c.get('url', '') for c in summary.get('ci_runs') or [] if c.get('url')),
           '_reviews': [(r.get('round'), r.get('verdict'), r.get('review_url', '')) for r in reviews],
           '_by_role': {role: dict(v) for role, v in by_role.items()}, '_sanitize': ''}
    errors = str(summary.get('stop_reason', '')) + ' '.join(str(r.get('error', '')) for r in reviews)
    if 'daily request quota' in errors:
        row['outcome'] = 'provider quota'           # infrastructure, not a pipeline result
    pr_number = int(summary['pr']) if str(summary.get('pr') or '').isdigit() else None
    for sid, item in seeded.items():
        if item['number'] == pr_number and summary.get('mode') == 'review':
            row.update(seeded_id=sid, expected_verdict=item['expected_verdict'],
                       reviewer_correct=bool(verdicts) and verdicts[-1] == item['expected_verdict'])
    return row


def pct(a: int, b: int) -> str:
    return f'{a}/{b} ({100 * a / b:.0f}%)' if b else '-'


def num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def full_metrics(items: list[dict]) -> dict:
    n = len(items)
    hp = sum(int(num(r['hidden_passed'])) for r in items)
    ht = sum(int(num(r['hidden_total'])) for r in items)
    return {
        'Runs': str(n),
        'PR opened and CI green (release passed)': pct(sum(r['release'] == 'passed' for r in items), n),
        'Stopped before release': pct(sum(r['outcome'] == 'stopped' for r in items), n),
        'Final review verdict: approve': pct(sum(r['final_verdict'] == 'approve' for r in items), n),
        'Mean review rounds': f"{sum(int(num(r['review_rounds'])) for r in items) / n:.2f}" if n else '-',
        'Hidden tests passed (no PR counts as all failed)': pct(hp, ht),
        'Runs passing every hidden test': pct(sum(1 for r in items if num(r['hidden_total']) and
                                                  r['hidden_passed'] == r['hidden_total']), n),
        'Mean failed stage checks per run': f"{sum(num(r['checks_failed']) for r in items) / n:.2f}" if n else '-',
        'Mean tokens per run': f"{sum(num(r['tokens_total']) for r in items) / n:,.0f}" if n else '-',
        'Mean estimated cost per run (USD)': f"{sum(num(r['est_cost_usd']) for r in items) / n:.2f}" if n else '-',
    }


def review_metrics(items: list[dict]) -> dict:
    bad = [r for r in items if r['expected_verdict'] == 'request_changes']
    good = [r for r in items if r['expected_verdict'] == 'approve']
    caught = sum(r['final_verdict'] == 'request_changes' for r in bad)
    missed = sum(r['final_verdict'] == 'approve' for r in bad)
    good_ok = sum(r['final_verdict'] == 'approve' for r in good)
    good_rejected = sum(r['final_verdict'] == 'request_changes' for r in good)
    verdicts: dict = defaultdict(list)
    for r in items:
        verdicts[r['seeded_id']].append(r['final_verdict'] or 'error')
    repeated = {pr: v for pr, v in verdicts.items() if len(v) > 1}
    consistent = sum(1 for v in repeated.values() if len(set(v)) == 1)
    flagged = caught + good_rejected
    return {
        'Reviews': str(len(items)),
        'Defects caught (recall on defective PRs)': pct(caught, len(bad)),
        'Defects missed (false approvals)': pct(missed, len(bad)),
        'Clean PRs approved': pct(good_ok, len(good)),
        'Clean PRs rejected (false alarms)': pct(good_rejected, len(good)),
        'Precision of "request changes"': pct(caught, flagged),
        'No verdict (review error)': str(len(items) - caught - missed - good_ok - good_rejected),
        'Same verdict on every repeat of a PR': pct(consistent, len(repeated)) if repeated else 'no repeats',
    }


def side_by_side(title: str, groups: dict[str, dict]) -> list[str]:
    names = list(groups)
    metrics = list(next(iter(groups.values())).keys()) if groups else []
    lines = [f'### {title}', '', '| Metric | ' + ' | '.join(names) + ' |', '|---' * (len(names) + 1) + '|']
    lines += [f'| {m} | ' + ' | '.join(groups[n][m] for n in names) + ' |' for m in metrics]
    return lines + ['']


def ordered(variants) -> list[str]:
    return sorted(set(variants), key=lambda v: (v != 'baseline', v))


def write_outputs(rows: list[dict], findings: dict, repo: str, out: Path, setup_runs: list[dict] = ()) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'results.csv', 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

    # ---- runs.md: every Actions run, PR, review and CI run -------------------------------------
    lines = ['# Runs', '', f'Every AutoSE run in https://github.com/{repo}, generated by '
             '`experiment/scripts/collect_results.py` from the runs themselves.', '',
             '| Run | Mode | Variant | Issue / seeded PR | PR | Outcome | Reviews | CI | Hidden tests | Tokens |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        pr = f"[#{r['pr']}]({r['pr_url']})" if r.get('pr_url') else (f"#{r['pr']}" if r.get('pr') else '-')
        reviews = ', '.join(f'[r{rnd}: {v}]({u})' if u else f'r{rnd}: {v}' for rnd, v, u in r['_reviews']) or '-'
        ci = ', '.join(f'[CI {i + 1}]({u})' for i, u in enumerate(r['ci_urls'].split())) or '-'
        hidden = f"{r['hidden_passed']}/{r['hidden_total']}" if r['hidden_total'] not in ('', None) else '-'
        target = r['seeded_id'] or r['issue_key'] or ''
        lines.append(f"| [{r['run_id']}]({r['run_url']}) | {r['mode']} | {r['variant']} | {target} #{r['issue']} | "
                     f"{pr} | {r['outcome']} | {reviews} | {ci} | {hidden} | {int(num(r['tokens_total'])):,} |")
    if setup_runs:
        lines += ['', '## Setup and verification runs', '', '| Run | Workflow | Conclusion |', '|---|---|---|']
        lines += [f"| [{s['run_id']}]({s['url']}) | AutoSE doctor | {s.get('conclusion')} |" for s in setup_runs]
    (out / 'runs.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # ---- summary.md -----------------------------------------------------------------------------
    issue_runs = [r for r in rows if r['mode'] == 'full' and r['kind'] != 'redteam' and r['outcome'] != 'provider quota']
    seeded_rows = [r for r in rows if r['seeded_id'] and r['outcome'] != 'provider quota']
    quota_runs = [r for r in rows if r['outcome'] == 'provider quota']
    md = ['# Results summary', '', '_Generated from real run artifacts by `collect_results.py`. Do not edit by hand._', '',
          f"Runs: {len(rows)} ({len([r for r in rows if r['mode'] == 'full'])} full, "
          f"{len([r for r in rows if r['mode'] == 'review'])} review-only). Tokens: "
          f"{sum(int(num(r['tokens_total'])) for r in rows):,} total; estimated cost "
          f"${sum(num(r['est_cost_usd']) for r in rows):.2f}."
          + (f" {len(quota_runs)} run(s) stopped by the model provider's daily quota are listed in runs.md "
             'but left out of every statistic below.' if quota_runs else ''), '']

    md += ['## Stage pass rate (full runs on the five issues, round 0)', '',
           'Share of runs that reached a stage and passed its check.', '',
           '| Variant | Runs | ' + ' | '.join(STAGES) + ' | review: approve |', '|---' * (len(STAGES) + 3) + '|']
    for variant in ordered(r['variant'] for r in issue_runs):
        items = [r for r in issue_runs if r['variant'] == variant]
        cells = []
        for stage in STAGES:
            reached = [r for r in items if r[stage] != 'not reached']
            cells.append(pct(sum(r[stage] == 'passed' for r in reached), len(reached)))
        reviewed = [r for r in items if r['review_rounds']]
        cells.append(pct(sum(r['final_verdict'] == 'approve' for r in reviewed), len(reviewed)))
        md.append(f'| {variant} | {len(items)} | ' + ' | '.join(cells) + ' |')
    md.append('')

    md += ['## Decision experiments, side by side', '']
    full_variants = ordered(r['variant'] for r in issue_runs)
    if len(full_variants) > 1:
        md += side_by_side('Full runs on the five issues',
                           {v: full_metrics([r for r in issue_runs if r['variant'] == v]) for v in full_variants})
    review_variants = ordered(r['variant'] for r in seeded_rows)
    if review_variants:
        md += side_by_side('Independent reviewer on the five seeded PRs',
                           {v: review_metrics([r for r in seeded_rows if r['variant'] == v]) for v in review_variants})

    md += ['## Hidden acceptance tests (head commit of each run)', '',
           '| Issue | Variant | Run | Passed | Note |', '|---|---|---|---|---|']
    for r in issue_runs:
        note = f"no PR: stopped at {r['stopped_stage']}" if not r['head_sha'] else ''
        md.append(f"| {r['issue_key']} | {r['variant']} | [{r['run_id']}]({r['run_url']}) | "
                  f"{r['hidden_passed']}/{r['hidden_total']} | {note} |")
    md.append('')

    judged = [r for r in issue_runs if r['review_rounds'] and num(r['hidden_total'])]
    if judged:
        def cell(verdict: str, all_pass: bool) -> int:
            return sum(1 for r in judged if r['final_verdict'] == verdict and
                       (r['hidden_passed'] == r['hidden_total']) == all_pass)
        md += ['## Reviewer verdict against the hidden tests (the workflow\'s own PRs)', '',
               'The hidden tests are ground truth the reviewer never saw.', '',
               '| Final verdict | All hidden tests pass | Some hidden test fails |', '|---|---|---|',
               f"| approve | {cell('approve', True)} (agreed) | {cell('approve', False)} (missed a defect) |",
               f"| request changes | {cell('request_changes', True)} (stricter than the tests) | "
               f"{cell('request_changes', False)} (agreed) |", '']

    if seeded_rows:
        md += ['## Reviewer on the seeded PRs, every review', '',
               '| Seeded PR | Variant | Repeat run | Expected | Verdict | Correct | Main findings |',
               '|---|---|---|---|---|---|---|']
        for r in seeded_rows:
            top = '; '.join(findings.get(r['run_id'], [])[:3]).replace('|', '/')[:300]
            md.append(f"| {r['seeded_id']} (#{r['pr']}) | {r['variant']} | [{r['run_id']}]({r['run_url']}) | "
                      f"{r['expected_verdict']} | {r['final_verdict'] or 'error'} | "
                      f"{'yes' if r['reviewer_correct'] else 'no'} | {top} |")
        md.append('')

    roles: dict = defaultdict(lambda: defaultdict(int))
    for r in rows:
        for role, slot in r['_by_role'].items():
            for k, v in slot.items():
                roles[role][k] += v
    if roles:
        md += ['## Tokens by role (all runs)', '', '| Role | Model calls | Uncached input | Output | Cache read | Cache write |',
               '|---|---|---|---|---|---|']
        md += [f"| {role} | {v['calls']:,} | {v['input']:,} | {v['output']:,} | {v['cache_read']:,} | {v['cache_write']:,} |"
               for role, v in sorted(roles.items())]
        md.append('')

    redteam = [r for r in rows if r['kind'] == 'redteam']
    if redteam:
        md += ['## Prompt-injection check (red-team issue)', '',
               '| Run | Outcome | PR | What the gate removed from the issue |', '|---|---|---|---|']
        md += [f"| [{r['run_id']}]({r['run_url']}) | {r['outcome']} | {r['pr_url'] or '-'} | {r['_sanitize'] or '-'} |"
               for r in redteam]
        md.append('')
    (out / 'summary.md').write_text('\n'.join(md) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--clone', required=True, type=Path)
    ap.add_argument('--python', default=sys.executable, help='python of a venv with pytest installed')
    ap.add_argument('--limit', type=int, default=300)
    ap.add_argument('--skip-hidden', action='store_true')
    args = ap.parse_args()
    guard(args.repo)
    issues = json.loads((ISSUES / 'index.json').read_text())
    seeded = json.loads((SEEDED / 'index.json').read_text()) if (SEEDED / 'index.json').exists() else {}
    runs = gh_json('run', 'list', '--repo', args.repo, '--workflow', 'autose.yml', '--limit', str(args.limit),
                   '--json', 'databaseId,status,conclusion,createdAt,url,event,displayTitle') or []
    cache = RESULTS / '.cache'
    rows, findings = [], {}
    for run in sorted(runs, key=lambda r: r['createdAt']):
        if run['status'] != 'completed':
            continue
        base = cache / str(run['databaseId'])
        folder = download(args.repo, run['databaseId'], 'autose-run-summary', base / 'summary')
        if not folder or not (folder / 'run_summary.json').exists():
            continue                                  # gate skipped: not an AutoSE run
        summary = json.loads((folder / 'run_summary.json').read_text())
        reviews = []
        for item in summary.get('reviews') or []:
            rd = download(args.repo, run['databaseId'], f"autose-review-r{item['round']}", base / f"review-r{item['round']}")
            if rd and (rd / 'review.json').exists():
                reviews.append(json.loads((rd / 'review.json').read_text()))
        row = build_row(run, summary, reviews, issues, seeded)
        findings[row['run_id']] = [f"[{f.get('severity')}] {f.get('description')}" for rv in reviews
                                   for f in ((rv.get('review') or {}).get('findings') or [])]
        if (row['mode'] == 'full' and row['issue_key'].startswith('issue_') and not args.skip_hidden
                and row['outcome'] != 'provider quota'):
            if row['head_sha']:
                hidden = hidden_for(args.clone, row['head_sha'], row['issue_key'], args.python)
                row.update(hidden_passed=hidden.get('passed', ''), hidden_total=hidden.get('total', ''))
            else:                                     # no PR: every hidden test counts as failed
                row.update(hidden_passed=0, hidden_total=hidden_count(row['issue_key']))
        if row['kind'] == 'redteam':
            snap = download(args.repo, run['databaseId'], 'autose-issue', base / 'issue')
            if snap and (snap / 'issue.json').exists():
                row['_sanitize'] = json.loads((snap / 'issue.json').read_text()).get('sanitize_note', '')
        rows.append(row)
        print(f"run {row['run_id']}: {row['mode']} {row['seeded_id'] or row['issue_key']} {row['variant']} -> {row['outcome']}")
    log = RESULTS / 'autopilot_log.json'
    setup_runs = json.loads(log.read_text()).get('doctor', []) if log.exists() else []
    write_outputs(rows, findings, args.repo, RESULTS, setup_runs)
    print(f'wrote {RESULTS}/results.csv, runs.md, summary.md ({len(rows)} runs)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
