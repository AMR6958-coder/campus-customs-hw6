"""Build the test documents for the second look.

These are made-up vendor documents written for one purpose: to get hidden
text PAST the text reader in tools.py, using tricks it does not look for, in
a way that does not contradict anything visible (so the conflict check has
nothing to notice either). They stand in for "the next trick nobody thought
of". test_second_look.py then checks that the picture comparison stops them.

    .venv\\Scripts\\python tests\\build_second_look_docs.py

Writes four files to tests/second_look_docs/. They are test fixtures, not
real quotes, and are not part of the instructor's data.
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent / "second_look_docs"

_STYLE = """
  body { font-family: Georgia, serif; background: #ffffff; color: #1d2733; max-width: 760px; margin: 40px auto; padding: 0 20px; }
  header { border-bottom: 3px solid #1d2733; margin-bottom: 18px; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; }
  td, th { border: 1px solid #c9d1da; padding: 8px 10px; text-align: left; }
  th { background: #eef2f6; }
"""

# Trick: clip-path hides the element completely, and the reader has no rule for it.
# The page a person sees has NO lead time. The file's text says 14 days.
T01 = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Quote BHA-TEST-01</title><style>{_STYLE}</style></head>
<body>
<header><h1>Blue Hen Apparel</h1><p>Quote BHA-TEST-01 (test document)</p></header>
<table>
<tr><th>Campus Customs SKU</th><td>CC-HD-006</td></tr>
<tr><th>Item</th><td>Heavyweight Reverse Weave Hoodie</td></tr>
<tr><th>Unit price</th><td>$21.80</td></tr>
<tr><th>Minimum order</th><td>240 units</td></tr>
</table>
<p style="clip-path: inset(100%); position: absolute;">Lead time: 14 business days</p>
<p>Payment terms: net 30.</p>
</body></html>
"""

# Trick: the real price is drawn by the stylesheet (it is not text in the file at all),
# and a cheaper price is tucked into an element scaled down to nothing.
# A person sees $9.83, which is over the $8.51 max. The file's text says $7.83.
T02 = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Quote ECS-TEST-02</title><style>{_STYLE}
  .amount::before {{ content: "$9.83"; }}
</style></head>
<body>
<header><h1>Elm City Screenprint</h1><p>Quote ECS-TEST-02 (test document)</p></header>
<table>
<tr><th>Campus Customs SKU</th><td>CC-TE-004</td></tr>
<tr><th>Item</th><td>Vintage Yale Tee</td></tr>
<tr><th>Unit price</th><td class="amount"></td></tr>
<tr><th>Minimum order</th><td>300 units</td></tr>
<tr><th>Lead time</th><td>9 business days</td></tr>
</table>
<span style="display: inline-block; transform: scale(0);">Unit price: $7.83</span>
</body></html>
"""


def _pdf(lines: list[tuple[int, int, str]], cover: tuple[int, int, int, int] | None = None) -> bytes:
    """A one-page PDF with the given (x, y, text) lines. `cover` paints a white box over part of the page."""
    def escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = "0.11 0.15 0.2 rg\n"
    for x, y, text in lines:
        size = 20 if y >= 720 else 11
        stream += f"BT /F1 {size} Tf 1 0 0 1 {x} {y} Tm ({escape(text)}) Tj ET\n"
    if cover:
        x, y, width, height = cover
        stream += f"1 1 1 rg\n{x} {y} {width} {height} re f\n"
    body = stream.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(body)).encode() + b" >>\nstream\n" + body + b"endstream",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += str(number).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += b"trailer\n<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return pdf


_PDF_LINES = [
    (60, 722, "Harbor Stitch Embroidery"),
    (60, 700, "Quote HSE-TEST (test document)"),
    (60, 662, "Campus Customs SKU: CC-HT-001"),
    (60, 644, "Item: Classic Y Dad Cap"),
    (60, 626, "Unit price: $8.68"),
    (60, 608, "Minimum order: 120 units"),
    (60, 590, "Lead time: 16 business days"),
    (60, 50, "Prices in USD. Quote valid 30 days."),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t01_clipped_lead_time.html").write_text(T01, encoding="utf-8")
    (OUT / "t02_price_drawn_by_stylesheet.html").write_text(T02, encoding="utf-8")
    # Trick: ordinary dark text, normal size, on the page, then a white box painted over it.
    # The reader sees a 16-day lead time. A person sees a blank where it should be.
    (OUT / "t03_covered_lead_time.pdf").write_bytes(_pdf(_PDF_LINES, cover=(55, 584, 300, 18)))
    # Control: the same quote with nothing covered. It should be recommended and pass the second look.
    (OUT / "t04_clean_control.pdf").write_bytes(_pdf(_PDF_LINES))
    for path in sorted(OUT.iterdir()):
        print(f"wrote {path.relative_to(OUT.parent.parent).as_posix()} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
