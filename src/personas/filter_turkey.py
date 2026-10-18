"""Extract the Turkey rows from the full WVS-7 cross-national file.

WVS distributes Wave 7 as one big cross-national file (all countries). Turkey
is country code 792 in the ``B_COUNTRY`` variable. This helper pulls just the
Turkey rows out and writes a local CSV for the ingest pipeline to read.

The output lives under the git-ignored ``data/`` dir and is never committed.

Usage:
    python -m src.personas.filter_turkey data/raw/WVS_Cross-National_Wave_7_csv_v6_0.csv
    # -> writes data/raw/wvs7_turkey.csv

    # other formats (Stata .dta / SPSS .sav) work too:
    python -m src.personas.filter_turkey "data/raw/WVS_TimeSeries_Stata.dta" --country 792
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.personas.ingest import load_raw

TURKEY_CODE = 792
COUNTRY_COLS = ("B_COUNTRY", "B_COUNTRY_ALPHA", "cntry", "COUNTRY")


def extract(input_path, output_path=None, country=TURKEY_CODE):
    df = load_raw(input_path)
    col = next((c for c in COUNTRY_COLS if c in df.columns), None)
    if col is None:
        raise SystemExit(
            f"No country column found (looked for {COUNTRY_COLS}). "
            "Check the file's codebook for the country variable name."
        )
    turkey = df[df[col].astype(str).str.strip() == str(country)]
    if turkey.empty:
        raise SystemExit(f"No rows with {col} == {country}. Is this the right file/code?")

    if output_path is None:
        output_path = Path(input_path).parent / "wvs7_turkey.csv"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    turkey.to_csv(output_path, index=False)
    print(f"Wrote {len(turkey)} Turkey rows -> {output_path}")
    return output_path


def main():
    ap = argparse.ArgumentParser(description="Extract Turkey rows from the WVS-7 file.")
    ap.add_argument("input", help="full WVS-7 cross-national file (.csv/.dta/.sav)")
    ap.add_argument("--out", default=None, help="output CSV path (default: data/raw/wvs7_turkey.csv)")
    ap.add_argument("--country", type=int, default=TURKEY_CODE, help="country code (Turkey = 792)")
    args = ap.parse_args()
    extract(args.input, args.out, args.country)


if __name__ == "__main__":
    main()
