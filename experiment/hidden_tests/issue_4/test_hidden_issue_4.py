"""Hidden acceptance tests for issue 4 (feature): ``operations.append``.

``append`` is imported inside each test so that a missing implementation
shows up as four individual failures instead of one collection error.
"""
import pytest

from tinydb import TinyDB, where
from tinydb.storages import MemoryStorage


def test_append_adds_value_to_an_existing_list():
    from tinydb.operations import append
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'ana', 'tags': ['a']})
    db.update(append('tags', 'b'), where('name') == 'ana')
    assert db.get(where('name') == 'ana')['tags'] == ['a', 'b']


def test_append_creates_the_list_when_the_field_is_missing():
    from tinydb.operations import append
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'ana'})
    db.update(append('tags', 'new'), where('name') == 'ana')
    assert db.get(where('name') == 'ana')['tags'] == ['new']


def test_append_on_many_documents_appends_exactly_once_to_each():
    from tinydb.operations import append
    db = TinyDB(storage=MemoryStorage)
    db.insert_multiple([{'n': 1}, {'n': 2}, {'n': 3}])
    db.update(append('tags', 'x'))
    assert [d['tags'] for d in db.all()] == [['x'], ['x'], ['x']]
    db.update(append('tags', 'y'), where('n') == 1)
    assert [d['tags'] for d in db.all()] == [['x', 'y'], ['x'], ['x']]


def test_append_to_a_non_list_field_raises_type_error():
    from tinydb.operations import append
    db = TinyDB(storage=MemoryStorage)
    db.insert({'name': 'ana', 'tags': 'oops'})
    with pytest.raises(TypeError):
        db.update(append('tags', 'b'), where('name') == 'ana')
