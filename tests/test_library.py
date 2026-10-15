import os
from datetime import datetime

from PIL import Image

import pytest

from chatdocket import ImageCollection, scan_folder


def save_png(path, timestamp):
    Image.new("RGB", (80, 120), "white").save(path)
    os.utime(path, (timestamp, timestamp))


def test_scan_folder_imports_supported_images_in_capture_order(tmp_path):
    later = datetime(2026, 3, 5, 11, 30).timestamp()
    earlier = datetime(2026, 3, 5, 9, 15).timestamp()
    save_png(tmp_path / "chat-2.png", later)
    save_png(tmp_path / "chat-1.png", earlier)
    (tmp_path / "notes.txt").write_text("not a screenshot")

    records = scan_folder(tmp_path)

    assert [record.filename for record in records] == ["chat-1.png", "chat-2.png"]
    assert records[0].captured_at == datetime.fromtimestamp(earlier)


def test_collection_accepts_a_complete_reorder(tmp_path):
    now = datetime(2026, 3, 5, 9, 15).timestamp()
    save_png(tmp_path / "chat-2.png", now)
    save_png(tmp_path / "chat-10.png", now)
    records = scan_folder(tmp_path)
    collection = ImageCollection(records)

    collection.reorder([records[1].id, records[0].id])

    assert [item.filename for item in collection.images] == ["chat-10.png", "chat-2.png"]


def test_collection_rejects_missing_or_duplicate_ids(tmp_path):
    now = datetime(2026, 3, 5, 9, 15).timestamp()
    save_png(tmp_path / "chat-1.png", now)
    save_png(tmp_path / "chat-2.png", now)
    collection = ImageCollection(scan_folder(tmp_path))

    with pytest.raises(ValueError, match="every imported image exactly once"):
        collection.reorder([collection.images[0].id, collection.images[0].id])
