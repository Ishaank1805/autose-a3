"""Hidden acceptance tests for issue 2 (bug):
``update_multiple()`` only applies updates to the first document when it is
given a generator instead of a list.
"""
from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage


def _catalog():
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple({'sku': f'A{i}', 'price': i} for i in range(1, 5))
    return db


def test_generator_updates_every_matching_document():
    db = _catalog()
    new_prices = {'A1': 10, 'A2': 20, 'A3': 30, 'A4': 40}
    db.update_multiple(
        ({'price': price}, where('sku') == sku)
        for sku, price in new_prices.items()
    )
    assert {d['sku']: d['price'] for d in db.all()} == new_prices


def test_generator_returns_the_ids_of_all_updated_documents():
    db = _catalog()
    ids = db.update_multiple(
        ({'price': 0}, where('sku') == sku) for sku in ['A2', 'A4']
    )
    assert sorted(ids) == [2, 4]


def test_generator_of_callable_updates():
    db = _catalog()

    def bump(doc):
        doc['price'] += 100

    db.update_multiple((bump, where('sku') == sku) for sku in ['A1', 'A3'])
    assert [d['price'] for d in db.all()] == [101, 2, 103, 4]


def test_list_input_still_works():
    db = _catalog()
    db.update_multiple([({'price': 7}, where('sku') == 'A1')])
    assert db.get(where('sku') == 'A1')['price'] == 7
