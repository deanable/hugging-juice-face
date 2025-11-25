from daminion_client import DaminionClient


def test_get_shared_collections_parses_list(monkeypatch):
    client = DaminionClient('https://example.test', 'u', 'p')

    def fake_request(endpoint, method='GET', data=None, timeout=30):
        # simulate API returning raw list
        return [{'id': 1, 'name': 'col1'}, {'id': 2, 'name': 'col2'}]

    client._make_request = fake_request

    cols = client.get_shared_collections()
    assert isinstance(cols, list)
    assert len(cols) == 2


def test_get_shared_collection_items_works(monkeypatch):
    client = DaminionClient('https://example.test', 'u', 'p')

    def fake_request(endpoint, method='GET', data=None, timeout=30):
        # emulate the mediaItems wrapper
        return {'mediaItems': [{'id': 5, 'fileName': 'x.jpg'}]}

    client._make_request = fake_request
    items = client.get_shared_collection_items(collection_id=123)
    assert isinstance(items, list)
    assert items[0]['id'] == 5


def test_get_flagged_items_filters(monkeypatch):
    client = DaminionClient('https://example.test', 'u', 'p')

    sample = [
        {'id': 1, 'fileName': 'good.jpg'},
        {'id': 2, 'fileName': 'rejected_one.png'},
        {'id': 3, 'fileName': 'ok.jpg', 'status': 'REJECTED'},
        {'id': 4, 'fileName': 'flagged_image.jpg'},
    ]

    client.get_all_items_paginated = lambda batch_size, max_items=None: sample

    flagged = client.get_flagged_items()
    ids = [it['id'] for it in flagged]
    assert 2 in ids and 3 in ids and 4 in ids
