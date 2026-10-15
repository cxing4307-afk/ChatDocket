import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image


SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}
EXIF_DATETIME_ORIGINAL = 36867
EXIF_DATETIME = 306


@dataclass(frozen=True)
class ImageRecord:
    path: Path
    captured_at: datetime

    @property
    def filename(self):
        return self.path.name

    @property
    def id(self):
        return str(self.path.resolve())

    def as_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "capturedAt": self.captured_at.isoformat(timespec="seconds"),
        }


class ImageCollection:
    def __init__(self, images):
        self.images = list(images)

    def reorder(self, ids):
        by_id = {image.id: image for image in self.images}
        if len(ids) != len(by_id) or set(ids) != set(by_id):
            raise ValueError("Order must contain every imported image exactly once")
        self.images = [by_id[image_id] for image_id in ids]


def _capture_time(path):
    with Image.open(path) as image:
        exif = image.getexif()
        raw = exif.get(EXIF_DATETIME_ORIGINAL) or exif.get(EXIF_DATETIME)
    if raw:
        try:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime)


def _natural_name(name):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", name)]


def scan_folder(folder):
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise ValueError("Choose an existing folder")

    records = [
        ImageRecord(path, _capture_time(path))
        for path in root.iterdir()
        if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
    ]
    return sorted(records, key=lambda item: (item.captured_at, _natural_name(item.filename)))
