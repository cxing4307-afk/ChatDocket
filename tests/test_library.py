import os
from datetime import datetime

from PIL import Image

from chatdocket import scan_folder


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
