from typing import Iterable

from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours
from locations.items import Feature
from locations.storefinders.location_smart import LocationSmartSpider

DETAIL_URL_TEMPLATE = "https://www.daiso-sangyo.co.jp/shop/detail/{shop_id}"


class DaisoSangyoJPSpider(LocationSmartSpider):
    name = "daiso_sangyo_jp"
    allowed_domains = ["daisosangyo.locationsmart.org", "www.daiso-sangyo.co.jp"]
    api_subdomain = "daisosangyo"

    # brand_id -> (brand name, wikidata id). CouCou has no wikidata item.
    BRANDS = {
        "daiso": ("ダイソー", "Q866991"),
        "threeppy": ("THREEPPY", "Q137916752"),
        "sp": ("Standard Products", "Q137916628"),
        "coucou": ("CouCou", None),
    }

    # Store names start with the brand prefix, the rest is the branch name,
    # e.g. "DAISO マルナカ三田店" -> branch "マルナカ三田店".
    BRAND_PREFIXES = {
        "daiso": "DAISO ",
        "threeppy": "THREEPPY ",
        "sp": "Standard Products ",
        "coucou": "CouCou ",
    }

    def post_process_item(self, item: Feature, response: Response, source_feature: dict) -> Iterable[Feature]:
        brand_name, wikidata = self.BRANDS[source_feature["brand_id"]]
        item["brand"] = brand_name
        if wikidata:
            item["brand_wikidata"] = wikidata
        if source_feature["brand_id"] != "daiso":
            # only daiso is in NSI which supplies its name
            item["name"] = brand_name
        else:
            item.pop("name", None)

        item["branch"] = source_feature["name"].removeprefix(self.BRAND_PREFIXES[source_feature["brand_id"]])
        item["website"] = DETAIL_URL_TEMPLATE.format(shop_id=source_feature["id"])
        item["opening_hours"] = self.parse_hours(source_feature["hours"])

        yield item

    def parse_detail_page(self, response: Response, item: Feature, source_feature: dict) -> Iterable[Feature]:
        address = "".join(response.xpath('//dt[text()="住所"]/following-sibling::dd[1]//text()').getall()).strip()
        if address:
            item["addr_full"] = address

        apply_category(Categories.SHOP_VARIETY_STORE, item)

        yield item

    @staticmethod
    def parse_hours(value: str) -> OpeningHours:
        opening_hours = OpeningHours()
        open_time, close_time = value.split("-", 1)
        opening_hours.add_days_range(DAYS, open_time, close_time)
        return opening_hours
