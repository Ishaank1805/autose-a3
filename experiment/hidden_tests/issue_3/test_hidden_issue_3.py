"""Hidden acceptance tests for issue 3 (feature): ``TinyDB.rename_table``."""
import pytest

from tinydb import Query, TinyDB
from tinydb.storages import MemoryStorage


def test_rename_keeps_documents_and_their_ids():
    db = TinyDB(storage=MemoryStorage)
    users = db.table('users')
    users.insert_multiple([{'name': 'ana'}, {'name': 'bo'}, {'name': 'cy'}])
    users.remove(doc_ids=[2])  # leave a gap so IDs are not simply 1..n
    db.rename_table('users', 'customers')
    assert 'users' not in db.tables()
    assert 'customers' in db.tables()
    moved = db.table('customers').all()
    assert [d['name'] for d in moved] == ['ana', 'cy']
    assert [d.doc_id for d in moved] == [1, 3]
    assert db.table('users').all() == []


def test_rename_is_persisted_to_the_json_file(tmp_path):
    path = tmp_path / 'db.json'
    with TinyDB(path) as db:
        db.table('users').insert({'name': 'ana'})
        db.rename_table('users', 'customers')
    with TinyDB(path) as db:
        assert db.tables() == {'customers'}
        assert db.table('customers').all() == [{'name': 'ana'}]


def test_rename_refuses_to_overwrite_an_existing_table():
    db = TinyDB(storage=MemoryStorage)
    db.table('users').insert({'name': 'ana'})
    db.table('customers').insert({'name': 'zed'})
    with pytest.raises((ValueError, KeyError)):
        db.rename_table('users', 'customers')
    assert db.table('users').all() == [{'name': 'ana'}]
    assert db.table('customers').all() == [{'name': 'zed'}]


def test_previously_opened_tables_do_not_return_stale_results():
    db = TinyDB(storage=MemoryStorage)
    User = Query()
    db.table('users').insert({'name': 'ana'})
    # Populate the query caches of both table objects before renaming.
    assert db.table('users').search(User.name == 'ana') == [{'name': 'ana'}]
    assert db.table('customers').search(User.name == 'ana') == []
    db.rename_table('users', 'customers')
    assert db.table('customers').search(User.name == 'ana') == [{'name': 'ana'}]
    assert db.table('users').search(User.name == 'ana') == []
