---
key: issue_2
kind: bug
title: "update_multiple() only updates the first record when given a generator"
labels: [bug]
---
I'm writing a small migration script that updates prices for a list of products. My first version looked like this:

```python
from tinydb import TinyDB, where

db = TinyDB('catalog.json')
new_prices = {'A1': 10, 'A2': 20, 'A3': 30}

db.update_multiple(
    ({'price': price}, where('sku') == sku)
    for sku, price in new_prices.items()
)
```

It ran without any error, but only the **first** product (A1) got its new price. A2 and A3 still have the old ones. The returned list of IDs also only contains `[1]`.

If I wrap the generator in `list(...)` everything works, so I can live with that for now, but it took me a while to notice because nothing fails. The type hint says `updates: Iterable[...]`, so I assumed a generator is fine. Either it should work with any iterable, or it should at least complain.

Same thing happens when the updates are functions (e.g. from `tinydb.operations`) instead of dicts.

TinyDB 4.9.0, Python 3.11.
