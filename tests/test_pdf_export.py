import re
from datetime import datetime

import pytest
from PIL import Image

from chatdocket import ImageRecord, export_pdf


def make_records(tmp_path, count):
    records = []
    for number in range(1, count + 1):
        path = tmp_path / f"chat-{number}.png"
        Image.new("RGB", (500, 900), (245, 245, 240)).save(path)
        records.append(ImageRecord(path, datetime(2026, 3, 5, 9, number)))
    return records


def test_export_paginates_an_a4_document(tmp_path):
    output = tmp_path / "packet.pdf"

    export_pdf(make_records(tmp_path, 3), output, per_page=2)

    pdf = output.read_bytes()
    assert pdf.startswith(b"%PDF-")
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) == 2
    assert b"/MediaBox [ 0 0 595.2756 841.8898 ]" in pdf


def test_export_rejects_an_unknown_layout(tmp_path):
    with pytest.raises(ValueError, match="1, 2, or 4"):
        export_pdf(make_records(tmp_path, 1), tmp_path / "packet.pdf", per_page=3)
