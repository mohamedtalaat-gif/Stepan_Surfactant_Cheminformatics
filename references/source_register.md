# Source register

Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University.

The data layer in `data/` was built from six Stepan seminar decks. `data/sources.csv` lists each file with its page count and SHA-256, so that anyone
holding the same deck can check it is the one used. Deck 5 of the numbered series was not among the supplied files. A second, identical copy of S2 was
supplied too; only one is kept. The decks were published by Azelis for the participants of the Stepan personal care customer seminar of October 2026, on
https://explore.azelis.com/en_GB/stepan-personal-care-customer-seminar-october-2026, which lists the same six.

| ID | Deck | Pages | What was captured |
| --- | --- | --- | --- |
| S1 | AOS in economical sulfate-free solutions | 39 | 12 charts, 7 prototype formulas, 3 chassis, product cards, regulatory timeline, additive ratings |
| S2 | Go sulfate free with our range of naturally derived ingredients | 29 | 6 charts (including a sensory radar), 7 formulas, product cards |
| S3 | STEPANBLEND ASF/MB | 26 | 5 charts, 3 formulas with process steps, technical data |
| S4 | Sulfate free for color care | 26 | 8 charts with error bars, 5 formulas, identity cards |
| S6 | Hair conditioning | 12 | 2 sensory charts, 3 formulas, structures of BTAC, CTAC and the ester quat |
| S7 | Sustainably sourced ingredients for haircare | 32 | 8 charts, 7 formulas, market statistics, claim-substantiation matrix |

## How values were taken

1. Chart values come from the drawing instructions inside the PDF, calibrated on the axis tick labels (`scripts/capture_charts.py`); four charts
   that are pictures were measured from the bitmap or read against the printed axis (`scripts/capture_raster.py`). The resolution is in `data/charts/_index.csv`.
2. A value printed beside a mark is kept as printed, with the drawn value beside it as a check.
3. `q.s.` is preserved as a q.s. instruction and is never converted into a guessed percentage; a printed total that does not add up to 100 is kept as printed.
4. A calculated value is arithmetic, not a new experimental result, and is labelled *derived* or *modelled* wherever it appears.
5. Results from different methods or conditions are not ranked as one series unless the slide does so.

## Withheld

Six pages of the supplied files are blank in the copies kept in `references/source_decks/` (page numbers unchanged), with a line saying why, and are listed
in the slide ledger as withheld: three held internal reviewer comments (S3 p20, S7 p2, S7 p3) and three held personal contact details (S4 p26, S6 p12, S7 p32).
The author, creator, keyword and subject fields of the files are empty. `scripts/redact_decks.py` does both and updates the checksums in `data/sources.csv`,
which are those of the copies kept here.
