---
key: issue_4
kind: feature
title: "Add an append operation for list fields"
labels: [enhancement]
---
I store tags as lists inside my documents, e.g. `{'title': 'Fix login', 'tags': ['backend']}`.

`tinydb.operations` already has `increment`, `add`, `set` and so on, which are really handy with `db.update()`. For lists I currently have to write a little function every time:

```python
def add_tag(doc):
    doc.setdefault('tags', []).append('urgent')

db.update(add_tag, where('title') == 'Fix login')
```

It would be nice to have this built in:

```python
from tinydb.operations import append

db.update(append('tags', 'urgent'), where('title') == 'Fix login')
```

If a document doesn't have the field yet, I'd expect it to just create the list (`['urgent']`). If the field exists but isn't a list (say someone stored a string by mistake), raising a `TypeError` would make sense to me rather than silently doing something weird.
