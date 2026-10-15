# ChatDocket 0.1 specification

ChatDocket is a local-only utility for turning a folder of chat screenshots into a printable evidence packet. It organizes images; it does not read messages, verify authenticity, or provide legal advice.

## User flow

1. Start the server and open the local web page.
2. Choose a folder containing `.jpg`, `.jpeg`, and `.png` files.
3. Review thumbnails in the default chronological order and drag cards to correct it.
4. Choose one, two, or four screenshots per A4 page.
5. Export a PDF to a path chosen by the user.

## Required behaviour

- Import only regular JPG, JPEG, and PNG files from the selected folder; do not recurse.
- Determine capture time from EXIF `DateTimeOriginal`, then EXIF `DateTime`, then filesystem modification time.
- Sort by capture time, using a natural filename order as the deterministic tie-breaker.
- Show each thumbnail with its source filename and capture time.
- Accept a reordered list only when it contains every imported image exactly once.
- Export portrait A4 PDFs with 1, 2, or 4 images per page.
- Preserve aspect ratio and EXIF orientation. Never crop screenshot content.
- Put a physical page number in the footer of every page.
- Put source filename and capture time beside each screenshot.
- Keep all user files local. Bind the HTTP server to `127.0.0.1` by default.
- Return useful JSON errors for invalid folders, reorder requests, layouts, and output paths.

## Explicit non-goals

- OCR, message extraction, annotation, redaction, authentication, cloud storage, recursive folder scans.
- Claims about admissibility, chain of custody, integrity, or legal effect.

## Public test seams

- `scan_folder(path)`: imported image metadata and ordering.
- `ImageCollection.reorder(ids)`: drag-order validation and resulting order.
- `export_pdf(images, output, per_page)`: readable A4 output and pagination.
- HTTP endpoints: observable request/response behaviour through a real local server.

## Dependencies and licensing

Runtime dependencies are Pillow 10.2.0 and ReportLab 5.0.1. ReportLab is BSD; its transitive `charset-normalizer` dependency is MIT. Pillow reports HPND in package metadata. HPND is permissive but is not literally MIT, BSD, or Apache; this exception is retained because Pillow is a mandated technology for this project and must be disclosed in the README. pytest and its transitive packages are development-only and permissively licensed.

## Acceptance checks

- A demo folder imports in chronological order and can be rearranged.
- The same images export successfully in all three layouts.
- Tests exercise EXIF/fallback ordering, natural filename ties, reorder rejection, PDF pagination, and HTTP errors.
- README includes actual commands, an actual UI screenshot, limitations, dependency licenses, and no legal promises.
