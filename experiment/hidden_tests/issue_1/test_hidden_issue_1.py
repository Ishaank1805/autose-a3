"""Hidden acceptance tests for issue 1 (bug):
``fragment()`` on different nested fields returns each other's results.

These tests live OUTSIDE the target repository so no agent can see them.
They FAIL on the pinned base commit and PASS on a correct fix.
"""
from tinydb import Query, TinyDB
from tinydb.storages import MemoryStorage


def _orders_db():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'billing': {'country': 'DE'}, 'shipping': {'country': 'FR'}})
    db.insert({'billing': {'country': 'FR'}, 'shipping': {'country': 'FR'}})
    return db


def test_fragment_on_different_paths_returns_independent_results():
    db = _orders_db()
    Order = Query()
    billing_de = db.search(Order.billing.fragment({'country': 'DE'}))
    shipping_de = db.search(Order.shipping.fragment({'country': 'DE'}))
    assert len(billing_de) == 1
    assert shipping_de == []


def test_fragment_queries_on_different_paths_are_not_equal():
    Order = Query()
    billing = Order.billing.fragment({'country': 'DE'})
    shipping = Order.shipping.fragment({'country': 'DE'})
    assert billing != shipping


def test_count_respects_fragment_path_when_called_back_to_back():
    db = _orders_db()
    Order = Query()
    assert db.count(Order.billing.fragment({'country': 'FR'})) == 1
    assert db.count(Order.shipping.fragment({'country': 'FR'})) == 2


def test_top_level_fragment_still_works():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'a': 1, 'b': 2})
    db.insert({'a': 1, 'b': 3})
    assert len(db.search(Query().fragment({'a': 1}))) == 2
    assert len(db.search(Query().fragment({'a': 1, 'b': 3}))) == 1
