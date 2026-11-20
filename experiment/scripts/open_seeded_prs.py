"""Open the five seeded reviewer-check PRs (known-good and known-bad) in your fork.

    python experiment/scripts/open_seeded_prs.py --repo YOU/tinydb --clone ../tinydb-fork

Each PR branch starts from the fork's main, gets one patch from
experiment/seeded_prs/, and is opened by you with its description and
"Refs #<issue>". The ground-truth label (seeded:approve / seeded:request-changes)
goes on the PR for humans; the reviewer never sees labels or PR descriptions
(in the baseline). Then trigger one independent review per PR, e.g.
    gh pr comment <pr> --repo YOU/tinydb --body "/autose review #<issue>"
Writes experiment/seeded_prs/index.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ISSUES, SEEDED, gh, gh_json, guard  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--clone', required=True, type=Path, help='a clean local clone of your fork')
    ap.add_argument('--base', default='main')
    args = ap.parse_args()
    guard(args.repo)

    def git(*a: str) -> str:
        return subprocess.run(['git', '-C', str(args.clone), *a], check=True, capture_output=True, text=True).stdout

    if git('status', '--porcelain').strip():
        raise SystemExit(f'{args.clone} has uncommitted changes')
    original = git('rev-parse', '--abbrev-ref', 'HEAD').strip()
    git('fetch', '-q', 'origin', args.base)
    issues = json.loads((ISSUES / 'index.json').read_text())
    prs = json.loads((SEEDED / 'seeded_prs.json').read_text())
    existing = gh_json('pr', 'list', '--repo', args.repo, '--state', 'all', '--limit', '200',
                       '--json', 'number,headRefName,url') or []
    for label in ('seeded', 'seeded:approve', 'seeded:request-changes'):
        gh('label', 'create', label, '--repo', args.repo, check=False)
    index = {}
    try:
        for pr in prs:
            issue = issues[pr['issue_key']]['number']
            hit = next((p for p in existing if p['headRefName'] == pr['branch']), None)
            if hit:
                number, url = hit['number'], hit['url']
                print(f"exists  #{number} {pr['id']}")
            else:
                git('checkout', '-q', '-B', pr['branch'], f'origin/{args.base}')
                git('apply', str(SEEDED / pr['patch']))
                git('add', '-A')
                git('commit', '-q', '-m', pr['title'])
                git('push', '-q', '-f', 'origin', pr['branch'])
                body = (SEEDED / f"{pr['id']}.md").read_text() + f'\n\nRefs #{issue}\n'
                url = gh('pr', 'create', '--repo', args.repo, '--base', args.base, '--head', pr['branch'],
                         '--title', pr['title'], '--body-file', '-', input=body).strip().splitlines()[-1]
                number = int(url.rstrip('/').rsplit('/', 1)[1])
                print(f"opened  #{number} {pr['id']} ({pr['expected_verdict']})")
            label = 'seeded:approve' if pr['expected_verdict'] == 'approve' else 'seeded:request-changes'
            gh('issue', 'edit', str(number), '--repo', args.repo, '--add-label', 'seeded', '--add-label', label)
            index[pr['id']] = {'number': number, 'url': url, 'issue': issue, 'branch': pr['branch'], 'set': pr.get('set', 'dev'),
                               'expected_verdict': pr['expected_verdict'], 'defect': pr['defect_category']}
    finally:
        git('checkout', '-q', original)
    (SEEDED / 'index.json').write_text(json.dumps(index, indent=2) + '\n')
    print('\nTrigger one review per seeded PR:')
    for sid, item in index.items():
        print(f"  gh pr comment {item['number']} --repo {args.repo} --body \"/autose review #{item['issue']}\"   # {sid}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
