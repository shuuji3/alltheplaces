# Data

Data files used by the spiders and library utilities in this repository.

## Japan prefecture and municipality codes

Japan's prefecture and municipality (都道府県/市区町村) codes, sourced from the
総務省統計局 publication 統計に用いる標準地域コード.

- **jp_prefectures.json** — the 47 prefectures, keyed by 2-digit JIS code.
- **jp_municipalities.json** — municipalities, keyed by the 5-digit
  全国地方公共団体コード.

Source: https://www.soumu.go.jp/toukei_toukatsu/index/seido/9-5.htm

### Update

Run the download + conversion script to fetch the latest CSV and regenerate the
JSON files:

    uv run python locations/data/update_jp_codes.py [CSV_URL]

### Access

Do not read these files directly. Use the accessor methods in
`locations/country_utils/jp.py` (see the module docstrings for the full API).
