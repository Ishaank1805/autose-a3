"""Draw report figures from results/results.csv (real runs only) into results/figures/.

    python experiment/scripts/make_figures.py        # needs matplotlib
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS  # noqa: E402

STAGES = ['requirements', 'design', 'implementation', 'testing', 'release']


def num(value) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def ordered(values) -> list[str]:
    return sorted(set(values), key=lambda v: (v != 'baseline', v))


def grouped_bars(ax, labels, series: dict[str, list[float]]) -> None:
    width = 0.8 / max(1, len(series))
    for i, (name, values) in enumerate(series.items()):
        ax.bar([x + i * width for x in range(len(labels))], values, width, label=name)
    ax.set_xticks([x + width * (len(series) - 1) / 2 for x in range(len(labels))], labels)
    ax.legend()


def main(results: Path = RESULTS) -> int:
    rows = list(csv.DictReader(open(results / 'results.csv', encoding='utf-8')))
    out = results / 'figures'
    out.mkdir(exist_ok=True)
    made = []
    rows = [r for r in rows if r['outcome'] != 'provider quota']
    full = [r for r in rows if r['mode'] == 'full' and r['kind'] != 'redteam']
    if full:
        series = {}
        for v in ordered(r['variant'] for r in full):
            items = [r for r in full if r['variant'] == v]
            rates = []
            for stage in STAGES:
                reached = [r for r in items if r[stage] != 'not reached']
                rates.append(100 * sum(r[stage] == 'passed' for r in reached) / len(reached) if reached else 0)
            series[f'{v} (n={len(items)})'] = rates
        fig, ax = plt.subplots(figsize=(8, 4))
        grouped_bars(ax, STAGES, series)
        ax.set(ylim=(0, 105), ylabel='% of runs that reached the stage', title='Stage pass rate by variant')
        fig.tight_layout(); fig.savefig(out / 'stage_pass_rate.png', dpi=160); plt.close(fig)
        made.append('stage_pass_rate.png')

        issues = sorted({r['issue_key'] for r in full})
        series = {}
        for v in ordered(r['variant'] for r in full):
            values = []
            for key in issues:
                items = [r for r in full if r['variant'] == v and r['issue_key'] == key and num(r['hidden_total'])]
                total = sum(num(r['hidden_total']) for r in items)
                values.append(100 * sum(num(r['hidden_passed']) for r in items) / total if total else 0)
            series[v] = values
        fig, ax = plt.subplots(figsize=(8, 4))
        grouped_bars(ax, issues, series)
        ax.set(ylim=(0, 105), ylabel='% of hidden tests passed', title='Hidden acceptance tests by issue and variant')
        fig.tight_layout(); fig.savefig(out / 'hidden_tests.png', dpi=160); plt.close(fig)
        made.append('hidden_tests.png')

    seeded = [r for r in rows if r['seeded_id']]
    if seeded:
        cats = [('defect caught', lambda r: r['expected_verdict'] == 'request_changes' and r['final_verdict'] == 'request_changes'),
                ('defect missed', lambda r: r['expected_verdict'] == 'request_changes' and r['final_verdict'] == 'approve'),
                ('clean PR approved', lambda r: r['expected_verdict'] == 'approve' and r['final_verdict'] == 'approve'),
                ('clean PR rejected', lambda r: r['expected_verdict'] == 'approve' and r['final_verdict'] == 'request_changes'),
                ('no verdict', lambda r: r['final_verdict'] not in ('approve', 'request_changes'))]
        variants = ordered(r['variant'] for r in seeded)
        fig, ax = plt.subplots(figsize=(7, 4))
        bottom = [0] * len(variants)
        for name, test in cats:
            values = [sum(1 for r in seeded if r['variant'] == v and test(r)) for v in variants]
            ax.bar(variants, values, bottom=bottom, label=name)
            bottom = [b + v for b, v in zip(bottom, values)]
        ax.set(ylabel='reviews', title='Independent reviewer on the seeded PRs')
        ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(out / 'seeded_reviews.png', dpi=160); plt.close(fig)
        made.append('seeded_reviews.png')

    if rows:
        groups = ordered(f"{r['mode']}:{r['variant']}" for r in rows)
        means = [sum(num(r['tokens_total']) for r in rows if f"{r['mode']}:{r['variant']}" == g)
                 / max(1, sum(1 for r in rows if f"{r['mode']}:{r['variant']}" == g)) for g in groups]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(groups, means)
        ax.set(ylabel='mean tokens per run', title='Token use per run')
        ax.tick_params(axis='x', labelrotation=20)
        fig.tight_layout(); fig.savefig(out / 'tokens_per_run.png', dpi=160); plt.close(fig)
        made.append('tokens_per_run.png')
    print('wrote', ', '.join(made) or 'no figures (no runs yet)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
