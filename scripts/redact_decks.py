# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Prepare the copies of the seminar decks that are kept in references/source_decks/.

    python scripts/redact_decks.py            # blank the withheld pages, clear the author fields, update the checksums in data/sources.csv

Pages that held internal reviewer comments or personal contact details are replaced by a blank page of the same size with one line saying why;
the page numbers do not change. The author, creator, keyword and subject fields of every file are cleared. Needs PyMuPDF (``uv sync --extra capture``).
Run it on the files as supplied; a second run finds the pages already withheld and only refreshes the checksums.
"""

from __future__ import annotations

import csv
import hashlib
import sys
import tempfile
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DECKS = ROOT / "references" / "source_decks"
SOURCES = ROOT / "data" / "sources.csv"

COMMENTS = "internal reviewer comments"
CONTACTS = "personal contact details"
WITHHELD = {
    "3._Super_Easy_solution_for_Sulfate_Free_STEPANBLEND_ASF-MB_mc5wnv.pdf": {20: COMMENTS},
    "4._Sulfate_Free_for_Color_Care_bve5ff.pdf": {26: CONTACTS},
    "6._Hair_Conditioning_tehdkl.pdf": {12: CONTACTS},
    "7._Sustainably_Sourced_Ingredients_for_Hair_Conditionning_gd8kwq.pdf": {2: COMMENTS, 3: COMMENTS, 32: CONTACTS},
}
CLEARED = ("author", "creator", "keywords", "subject")


def prepare(path: Path) -> None:
    doc = pymupdf.open(path)
    for number, why in WITHHELD.get(path.name, {}).items():
        if doc[number - 1].get_text().startswith("Page withheld"):
            continue
        size = doc[number - 1].rect
        doc.delete_page(number - 1)
        page = doc.new_page(number - 1, width=size.width, height=size.height)
        page.insert_text((72, 100), f"Page withheld in this copy: it held {why}, not seminar content.", fontsize=12, fontname="helv")
    meta = doc.metadata
    for key in CLEARED:
        meta[key] = ""
    doc.set_metadata(meta)
    doc.del_xml_metadata()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=path.parent) as tmp:
        tmp_path = Path(tmp.name)
    doc.save(tmp_path, garbage=4, deflate=True, clean=True)
    doc.close()
    tmp_path.replace(path)


def main() -> None:
    for pdf in sorted(DECKS.glob("*.pdf")):
        prepare(pdf)
        print("prepared", pdf.name)
    with SOURCES.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = rows[0].keys()
    for row in rows:
        row["sha256"] = hashlib.sha256((DECKS / row["file"]).read_bytes()).hexdigest()
    with SOURCES.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("checksums written to", SOURCES)


if __name__ == "__main__":
    sys.exit(main())
