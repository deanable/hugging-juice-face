import os
from pathlib import Path

import pytest

from gui_handlers_modern import filter_local_images, filter_daminion_items


def create_files(base: Path, files):
    paths = []
    for f in files:
        p = base / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("dummy")
        paths.append(p)
    return paths


def test_filter_local_collection(tmp_path):
    base = tmp_path / "images"
    files = ["a.jpg", "collection1/one.jpg", "collection1/sub/two.png", "other/three.jpg"]
    paths = create_files(base, files)
    all_images = list(base.rglob("*.*"))

    collection_path = base / "collection1"
    filtered = filter_local_images(all_images, 'collection', collection_path)
    assert len(filtered) == 2
    assert all(collection_path in p.parents or str(p).startswith(str(collection_path)) for p in filtered)


def test_filter_local_flagged(tmp_path):
    base = tmp_path / "images"
    files = ["normal.jpg", "flagged_one.jpg", "sub/rejected_image.png", "good.png"]
    paths = create_files(base, files)
    all_images = list(base.rglob("*.*"))

    filtered = filter_local_images(all_images, 'flagged')
    names = [p.name for p in filtered]
    assert 'flagged_one.jpg' in names
    assert 'rejected_image.png' in names


def test_filter_daminion_flagged():
    items = [
        {'id': 1, 'fileName': 'OK.jpg'},
        {'id': 2, 'fileName': 'flagged_photo.JPG'},
        {'id': 3, 'fileName': 'other.png', 'status': 'rejected'},
        {'id': 4, 'fileName': 'fine.jpg', 'keywords': ['sun','beach']}
    ]

    filtered = filter_daminion_items(items, 'flagged')
    ids = [it['id'] for it in filtered]
    assert 2 in ids and 3 in ids


def test_filter_daminion_collection():
    items = [
        {'id': 1, 'fileName': 'kitchen_one.jpg'},
        {'id': 2, 'fileName': 'bedroom_two.jpg'},
        {'id': 3, 'fileName': 'kitchen_three.png'}
    ]

    filtered = filter_daminion_items(items, 'collection', 'kitchen')
    assert len(filtered) == 2


def test_filter_untagged_returns_all(tmp_path):
    base = tmp_path / "images"
    files = ["a.jpg", "b.png"]
    create_files(base, files)
    all_images = list(base.rglob("*.*"))

    assert filter_local_images(all_images, 'untagged') == all_images

    items = [{'id': 1, 'fileName': 'x.jpg'}]
    assert filter_daminion_items(items, 'untagged') == items
