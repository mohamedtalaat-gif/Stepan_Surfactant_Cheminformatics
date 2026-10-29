# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
"""Serve the start page, the six session notebooks and the labs from one process.

    python -m uvicorn server:app --port 2718

The start page is at "/", each notebook at "/<notebook name>"; the links in the notebooks point there.
"""

from pathlib import Path

import marimo

from stepan_lab.provenance import CITATION, SOURCE_NOTICE

NOTEBOOKS = Path(__file__).resolve().parent / "notebooks"

_server = marimo.create_asgi_app().with_app(path="/", root=str(NOTEBOOKS / "start_here.py"))
for _nb in sorted(NOTEBOOKS.glob("*.py")):
    if _nb.stem != "start_here":
        _server = _server.with_app(path=f"/{_nb.stem}", root=str(_nb))

print(CITATION)
print(SOURCE_NOTICE)
app = _server.build()
