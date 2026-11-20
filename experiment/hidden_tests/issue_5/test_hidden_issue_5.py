"""Hidden acceptance tests for issue 5 (vague):
"printing search results is unhelpful".

These encode ONE reasonable interpretation: a printed ``Document`` shows its
``doc_id`` while still behaving exactly like a dict. An agent that picks a
different but defensible interpretation will fail them; that is the point of
the vague issue and belongs in the report's discussion.
"""
import json

from tinydb import TinyDB
from tinydb.storages import MemoryStorage
from tinydb.table import Document


def _db():
    db = TinyDB(storage=MemoryStorage)
    db.insert(Document({'name': 'ana'}, doc_id=4242))
    db.insert(Document({'name': 'bo'}, doc_id=7331))
    return db


def test_printed_document_shows_its_doc_id():
    doc = _db().get(doc_id=4242)
    assert '4242' in str(doc)
    assert '4242' in repr(doc)


def test_printed_document_still_shows_its_fields():
    text = repr(_db().get(doc_id=4242))
    assert 'name' in text and 'ana' in text


def test_printed_result_lists_show_every_doc_id():
    out = str(_db().all())
    assert '4242' in out and '7331' in out


def test_document_still_behaves_like_a_plain_dict():
    doc = _db().get(doc_id=4242)
    assert doc == {'name': 'ana'}
    assert dict(doc) == {'name': 'ana'}
    assert json.loads(json.dumps(doc)) == {'name': 'ana'}
