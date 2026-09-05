import re
import unicodedata
from typing import Iterable

from scrapy.http import Request, Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours
from locations.items import Feature
from locations.storefinders.location_smart import LocationSmartSpider


class YaokoJPSpider(LocationSmartSpider):
    """Extract Yaoko (JP) store details from the official main website.

    Coords are not present on the main site, so they need to be fetched from
    the LocationSmart store-locator API, and it builds a ``branch -> (lat, lon)``
    map. Then, the main site's store list is crawled and each store is filled
    with coordinates by matching branch name if any.

    The API does not cover every main-site store: stores that only publish
    employee (社員) postings have no coords in any source, so those are left
    without coordinates as best effort.
    """

    name = "yaoko_jp"
    item_attributes = {
        "brand": "ヤオコー",
        "brand_wikidata": "Q11344967",
    }
    api_subdomain = "job01"
    api_map_id = "yaoko"
    store_list_url = "https://www.yaoko-net.com/store/"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_to_coords_map: dict[str, tuple[float, float]] = {}

    def parse(self, response: Response):
        yield from super().parse(response)
        yield Request(self.store_list_url, callback=self.parse_store_list)

    def parse_shop(self, response: Response, shop: dict) -> Iterable[Feature]:
        """Build the branch -> coords map from each shop; no item is yielded."""
        branch = re.sub(r"\s*ヤオコー\s*", "", shop["name"])
        key = self.branch_key(branch)
        self.branch_to_coords_map[key] = (float(shop["lat"]), float(shop["lon"]))
        yield from ()

    def parse_store_list(self, response: Response):
        seen: set[str] = set()
        for url in response.xpath("//a[contains(@href, '/store/store') and contains(@href, '.html')]/@href").getall():
            url = response.urljoin(url)
            if url in seen:
                continue
            seen.add(url)
            yield Request(url, callback=self.parse_store)

    def parse_store(self, response: Response):
        trs = response.xpath("//table[contains(@class, 'store_info_table')]//tr")
        info = {
            label: value
            for tr in trs
            if (label := tr.xpath("./th/text()").get(""))
            for value in [tr.xpath("string(./td)").get("")]
        }

        item = Feature()
        item["name"] = "ヤオコー"
        item["ref"] = response.url.rstrip("/").split("/")[-1].replace(".html", "")
        item["branch"] = re.sub(r"（.*?）$", "", response.xpath("//h1/text()").get("")).strip()
        item["website"] = response.url
        item["country"] = "JP"

        addr_lines = [line.strip() for line in info.get("住所", "").split("\n") if line.strip()]
        item["addr_full"] = re.sub(r"〒\s*[0-9\-]+\s*", "", "\n".join(addr_lines)).strip()
        postcode = re.search(r"〒\s*([0-9\-]+)", info.get("住所", ""))
        if postcode:
            item["postcode"] = postcode.group(1)
        item["phone"] = info.get("電話番号", "").strip()
        item["opening_hours"] = self.parse_hours(info.get("営業時間", "").strip())

        coords = self.branch_to_coords_map.get(self.branch_key(item["branch"]))
        if coords:
            item["lat"], item["lon"] = coords

        apply_category(Categories.SHOP_SUPERMARKET, item)

        yield item

    @staticmethod
    def branch_key(name: str) -> str:
        name = unicodedata.normalize("NFKC", name)
        name = re.sub(r"ヤオコー", "", name)
        name = re.sub(r"\s+", "", name)
        name = re.sub(r"[（(][^）)]*[）)]$", "", name)
        return name.strip()

    @staticmethod
    def parse_hours(text: str) -> OpeningHours:
        oh = OpeningHours()
        line = re.sub(r"\s", "", text.replace("：", ":").replace("～", "-").replace("〜", "-"))
        m = re.search(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})", line)
        if m:
            oh.add_days_range(DAYS, m.group(1), m.group(2))
        return oh
