import json
from pathlib import Path

from locations.country_utils.jp_types import JPMunicipality, JPPrefecture, JPPrefectureCode, JPPrefectureName

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class JapanUtils:
    """Japan prefecture and municipality accessors, mirroring geonamescache.

    Mirrors geonamescache's ``GeonamesCache``: datasets are lazy-loaded once
    into instance attributes via ``_load_data`` and re-keyed by name via
    ``get_dataset_by_key``.
    """

    prefectures: dict[JPPrefectureCode, JPPrefecture] | None = None
    municipalities: dict[str, JPMunicipality] | None = None

    def get_prefectures(self) -> dict[JPPrefectureCode, JPPrefecture]:
        """Return Japan's 47 prefectures keyed by 2-digit JIS code.

        Mirrors geonamescache's ``get_us_states()``: each record carries the
        JIS prefecture code (``code``) and the official Japanese name (``name``).
        """
        return self._load_data(self.prefectures, "jp_prefectures.json")

    def get_prefectures_by_names(self) -> dict[JPPrefectureName, JPPrefecture]:
        """Return Japan's 47 prefectures keyed by official Japanese name.

        Mirrors geonamescache's ``get_us_states_by_names()``.
        """
        return self.get_dataset_by_key(self.get_prefectures(), "name")

    def get_municipalities(self) -> dict[str, JPMunicipality]:
        """Return Japan's municipalities keyed by 5-digit JIS code.

        Mirrors geonamescache's ``get_us_counties()``: each record carries the
        全国地方公共団体コード (``code``), the municipality name (``name``), and the
        parent prefecture code (``pref_code``).
        """
        return self._load_data(self.municipalities, "jp_municipalities.json")

    def get_municipalities_by_names(self) -> dict[str, JPMunicipality]:
        """Return Japan's municipalities keyed by name.

        Mirrors geonamescache's ``get_us_counties``-by-name accessor.
        """
        return self.get_dataset_by_key(self.get_municipalities(), "name")

    @staticmethod
    def _load_data(datadict: dict[str, dict] | None, datafile: str) -> dict[str, dict]:
        if datadict is None:
            with open(_DATA_DIR / datafile, encoding="utf-8") as f:
                datadict = json.load(f)
        return datadict

    @staticmethod
    def get_dataset_by_key(dataset: dict[str, dict], key: str) -> dict[str, dict]:
        return {record[key]: record for record in dataset.values()}
