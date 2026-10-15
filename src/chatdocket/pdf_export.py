from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def _grid(per_page):
    return {1: (1, 1), 2: (1, 2), 4: (2, 2)}[per_page]


def _fit(width, height, max_width, max_height):
    scale = min(max_width / width, max_height / height)
    return width * scale, height * scale


def export_pdf(images, output, per_page=2):
    if per_page not in {1, 2, 4}:
        raise ValueError("Screenshots per page must be 1, 2, or 4")
    if not images:
        raise ValueError("Import at least one screenshot before exporting")

    destination = Path(output).expanduser()
    if destination.suffix.casefold() != ".pdf":
        destination = destination.with_suffix(".pdf")
    if not destination.parent.is_dir():
        raise ValueError("The output folder does not exist")

    page_width, page_height = A4
    margin = 34
    footer_height = 24
    columns, rows = _grid(per_page)
    usable_width = page_width - margin * 2
    usable_height = page_height - margin * 2 - footer_height
    cell_width = usable_width / columns
    cell_height = usable_height / rows
    metadata_height = 30
    doc = canvas.Canvas(str(destination), pagesize=A4, pageCompression=0)

    for offset in range(0, len(images), per_page):
        page_images = images[offset : offset + per_page]
        for position, record in enumerate(page_images):
            column = position % columns
            row = position // columns
            cell_x = margin + column * cell_width
            cell_top = page_height - margin - row * cell_height
            image_bottom = cell_top - cell_height + metadata_height
            max_width = cell_width - 16
            max_height = cell_height - metadata_height - 12

            with Image.open(record.path) as source:
                prepared = ImageOps.exif_transpose(source).convert("RGB")
                draw_width, draw_height = _fit(
                    prepared.width, prepared.height, max_width, max_height
                )
                x = cell_x + (cell_width - draw_width) / 2
                y = image_bottom + (max_height - draw_height) / 2
                doc.drawImage(
                    ImageReader(prepared), x, y, draw_width, draw_height, preserveAspectRatio=True
                )

            doc.setFont("Helvetica", 8)
            doc.drawCentredString(
                cell_x + cell_width / 2,
                cell_top - cell_height + 17,
                record.filename,
            )
            doc.setFillColorRGB(0.35, 0.35, 0.35)
            doc.drawCentredString(
                cell_x + cell_width / 2,
                cell_top - cell_height + 7,
                record.captured_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
            doc.setFillColorRGB(0, 0, 0)

        page_number = offset // per_page + 1
        doc.setFont("Helvetica", 9)
        doc.drawCentredString(page_width / 2, 16, f"Page {page_number}")
        doc.showPage()

    doc.save()
    return destination
