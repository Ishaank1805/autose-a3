"""Open the five experiment issues (and optionally the red-team issue) in your fork.

    python experiment/scripts/open_issues.py --repo YOU/tinydb [--include-redteam]

Idempotent: an issue whose exact title already exists is reused. Writes
experiment/issues/index.json (issue key -> number, url, kind).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ISSUES, gh, gh_json, guard, read_issue  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--include-redteam', action='store_true')
    args = ap.parse_args()
    guard(args.repo)
    files = sorted(ISSUES.glob('issue_*.md'))
    if args.include_redteam:
        files += sorted(p for p in (ISSUES / 'extra').glob('*.md') if p.name != 'README.md')
    existing = gh_json('issue', 'list', '--repo', args.repo, '--state', 'all', '--limit', '300',
                       '--json', 'number,title,url') or []
    index_path = ISSUES / 'index.json'
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    for path in files:
        meta, body = read_issue(path)
        hit = next((i for i in existing if i['title'] == meta['title']), None)
        if hit:
            number, url = hit['number'], hit['url']
            print(f"exists  #{number} {meta['title']}")
        else:
            labels = meta.get('labels') or []
            for label in labels:
                gh('label', 'create', label, '--repo', args.repo, check=False)  # fails harmlessly if present
            label_args = [arg for label in labels for arg in ('--label', label)]
            url = gh('issue', 'create', '--repo', args.repo, '--title', meta['title'], '--body-file', '-',
                     *label_args, input=body).strip().splitlines()[-1]
            number = int(url.rstrip('/').rsplit('/', 1)[1])
            print(f"opened  #{number} {meta['title']}")
        index[meta['key']] = {'number': number, 'url': url, 'title': meta['title'], 'kind': meta.get('kind')}
    index_path.write_text(json.dumps(index, indent=2) + '\n')
    print(f'wrote {index_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
