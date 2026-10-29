# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Each notebook is run from top to bottom in its own process; a failing cell fails the test."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.py"))


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_runs_without_a_failing_cell(path):
    done = subprocess.run([sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True, timeout=600)
    assert done.returncode == 0, done.stderr[-1500:]
    assert "Traceback" not in done.stderr, done.stderr[-1500:]


def test_every_source_file_carries_the_credit_header():
    files = [*NOTEBOOKS, ROOT / "server.py", *(ROOT / "src").rglob("*.py"), *(ROOT / "scripts").glob("*.py"), *(ROOT / "tests").glob("*.py")]
    missing = [str(f.relative_to(ROOT)) for f in files if "Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University" not in f.read_text()[:400]]
    assert not missing, missing
