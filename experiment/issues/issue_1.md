---
key: issue_1
kind: bug
title: "fragment() on a nested field returns matches from a different field"
labels: [bug]
---
Hi! I think I ran into a caching problem with `fragment()` when it's used on nested fields.

I store orders with a billing and a shipping address and wanted all orders that ship to Germany:

```python
from tinydb import TinyDB, Query

db = TinyDB('orders.json')
Order = Query()

db.insert({'billing': {'country': 'DE'}, 'shipping': {'country': 'FR'}})
db.insert({'billing': {'country': 'FR'}, 'shipping': {'country': 'FR'}})

print(db.search(Order.billing.fragment({'country': 'DE'})))   # 1 result, correct
print(db.search(Order.shipping.fragment({'country': 'DE'})))  # ALSO returns the first order?!
```

The second search should return nothing (no order ships to DE), but it returns the order whose *billing* country is DE. If I call `db.clear_cache()` between the two searches the second one is correct, so it looks like the query cache thinks the two queries are the same query. And indeed:

```python
>>> Order.billing.fragment({'country': 'DE'}) == Order.shipping.fragment({'country': 'DE'})
True
```

`db.count()` gives wrong numbers the same way, I guess because it goes through `search()`. A plain top-level `Query().fragment({...})` seems to work fine.

TinyDB 4.9.0, Python 3.12 on Ubuntu 24.04.
