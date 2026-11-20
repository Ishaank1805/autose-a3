---
key: issue_3
kind: feature
title: "Feature request: rename a table"
labels: [enhancement]
---
We keep different kinds of records in separate tables and decided to rename our `users` table to `customers`. There is `drop_table()` but I couldn't find a way to rename a table.

What I'm doing now:

```python
for doc in db.table('users').all():
    db.table('customers').insert(doc)
db.drop_table('users')
```

That's clunky, it changes the document IDs (we store those IDs elsewhere, so that's a real problem for us), and if the script dies halfway through I end up with the data in both tables or only partly copied.

It would be great to have something like:

```python
db.rename_table('users', 'customers')
```

Things that matter to me:

- the documents **and their IDs** should stay exactly the same, just under the new name
- it should of course be saved to the JSON file like any other change
- if a table with the new name already exists it should refuse instead of silently overwriting that table's data
- I keep table objects around in my app (`users = db.table('users')` at startup), so whatever this does, please make sure I don't get stale results afterwards

Thanks for TinyDB, it's been great for our small internal tool!
