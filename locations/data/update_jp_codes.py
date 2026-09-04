#!/usr/bin/env python3
"""Download and convert the 総務省 統計に用いる標準地域コード to JSON.

Downloads the first-party authoritative CSV from 総務省統計局 and writes
``jp_prefectures.json`` and ``jp_municipalities.json`` in this directory.

Usage:
    python update_jp_codes.py [CSV_URL]
"""

import argparse
import csv
import io
import json
import urllib.request
from pathlib import Path

_DEFAULT_URL = "https://www.soumu.go.jp/main_content/000323625.csv"
_DATA_DIR = Path(__file__).resolve().parent


def fetch(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        raw = response.read()
    return raw.decode("cp932")


def convert(source: str) -> tuple[dict[str, dict], dict[str, dict]]:
    rows = list(csv.DictReader(io.StringIO(source)))
    prefectures: dict[str, dict] = {}
    municipalities: dict[str, dict] = {}
    for row in rows:
        if row["sityouson-code"] == "000":
            prefectures[row["ken-code"]] = {
                "code": row["ken-code"],
                "name": row["ken-name"],
                "ja_hira": row["yomigana"],
            }
        else:
            name = row["sityouson-name1"] or row["sityouson-name2"] or row["sityouson-name3"]
            municipalities[row["tiiki-code"]] = {
                "code": row["tiiki-code"],
                "name": name,
                "pref_code": row["ken-code"],
                "ja_hira": row["yomigana"],
            }
    return prefectures, municipalities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=_DEFAULT_URL)
    args = parser.parse_args()

    source = fetch(args.url)
    prefectures, municipalities = convert(source)

    with open(_DATA_DIR / "jp_prefectures.json", "w", encoding="utf-8") as f:
        json.dump(prefectures, f, ensure_ascii=False, indent=2)
    with open(_DATA_DIR / "jp_municipalities.json", "w", encoding="utf-8") as f:
        json.dump(municipalities, f, ensure_ascii=False, indent=2)

    print(f"wrote {len(prefectures)} prefectures, {len(municipalities)} municipalities")


if __name__ == "__main__":
    main()
