# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT

"""Authorship and the notice that every entry point prints."""

__version__ = "1.0.0"

AUTHOR = "Muhammad Talaat"
AFFILIATION = "Faculty of Pharmacy, Ain Shams University"
ORCID = "0000-0002-9171-437X"
CREDIT_LINE = f"Created by {AUTHOR}, {AFFILIATION}"

SOURCE_NOTICE = (
    "The seminar data come from the Stepan Company hair-care seminar decks. Product names and the "
    "registered marks in them belong to Stepan Company. The calculations, models, notebooks and all "
    "explanatory text are independent work and are not Stepan statements."
)

CITATION = (
    f"{AUTHOR}, {AFFILIATION} (ORCID {ORCID}). Stepan Surfactant Chemistry: a Cheminformatics Dry Lab, version {__version__}."
)
