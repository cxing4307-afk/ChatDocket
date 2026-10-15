"""Create the fictional screenshots used in the README demo."""

import os
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "sample-chat"


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def bubble(draw, text, y, mine=False):
    body = font(25)
    box = draw.textbbox((0, 0), text, font=body)
    width = box[2] - box[0] + 42
    left = 740 - width if mine else 28
    color = "#d9fdd3" if mine else "#ffffff"
    draw.rounded_rectangle((left, y, left + width, y + 62), 18, fill=color)
    draw.text((left + 21, y + 16), text, font=body, fill="#202521")
    return y + 82


def make_page(number, messages, stamp):
    image = Image.new("RGB", (768, 1365), "#e7e1d7")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 768, 116), fill="#f8f6f0")
    draw.ellipse((24, 24, 88, 88), fill="#bacbb7")
    draw.text((108, 31), "Morgan", font=font(27, True), fill="#1d261f")
    draw.text((108, 69), "Project handoff", font=font(18), fill="#6a746c")
    draw.line((0, 115, 768, 115), fill="#d0cbc2", width=2)
    y = 156
    for text, mine in messages:
        y = bubble(draw, text, y, mine)
    draw.text((28, 1318), f"Fictional demo • page {number}", font=font(17), fill="#777a76")
    path = OUT / f"chat-{number}.png"
    image.save(path)
    moment = datetime.strptime(stamp, "%Y-%m-%d %H:%M").timestamp()
    os.utime(path, (moment, moment))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [
        ([('Can you send the final handoff time?', False), ('Yes — Thursday at 10:00.', True), ('I will have the archive ready.', True)], "2026-03-05 09:12"),
        ([('Got it. Include the signed checklist?', False), ('Yes, plus the February notes.', True), ('I will put both in the folder.', True)], "2026-03-05 09:18"),
        ([('The download link expires Friday.', False), ('Downloaded and backed up.', True), ('Thanks. That closes it out.', False)], "2026-03-05 09:24"),
        ([('One correction: use revision 3.', False), ('Understood — revision 3 only.', True), ('Confirmed.', False)], "2026-03-05 09:31"),
    ]
    for index, (messages, stamp) in enumerate(pages, 1):
        make_page(index, messages, stamp)
    print(f"Wrote {len(pages)} demo screenshots to {OUT}")


if __name__ == "__main__":
    main()
