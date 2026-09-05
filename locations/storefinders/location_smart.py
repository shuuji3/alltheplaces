from typing import AsyncIterator, Iterable

from scrapy import Spider
from scrapy.http import JsonRequest, Request, Response

from locations.dict_parser import DictParser
from locations.items import Feature


class LocationSmartSpider(Spider):
    """
    Store-finder API served by LocationSmart at ``<subdomain>.locationsmart.org``.

    The "g2" JSON endpoint returns every shop in a single response::

        {"shops": [{"id": ..., "lat": ..., "lon": ..., "name": ...}]}

    Subclasses set :attr:`subdomain` (and optionally :attr:`map_id`) and override
    :meth:`post_process_item` to add brand-specific fields. To also enrich each
    item from a per-store detail page, override :meth:`parse_detail_page`; the
    storefinder then fetches ``item["website"]`` automatically and passes the
    response to that hook.
    """

    dataset_attributes: dict = {"source": "api", "api": "locationsmart.org"}
    api_subdomain: str
    api_map_id: str | None = None

    async def start(self) -> AsyncIterator[JsonRequest]:
        """Request the full shop list from the g2 JSON endpoint."""
        yield JsonRequest(url=self.build_url())

    def build_url(self) -> str:
        """Build the g2 API URL from :attr:`subdomain` and optional :attr:`map_id`."""
        url = f"https://{self.api_subdomain}.locationsmart.org/map/g2?n=90&s=0&w=0&e=179&z=99"
        if self.api_map_id:
            url += f"&map_id={self.api_map_id}"
        return url

    def parse(self, response: Response) -> Iterable[Feature]:
        """Parse the shop list, yielding a Feature per shop."""
        for shop in response.json()["shops"]:
            yield from self.parse_shop(response, shop) or []

    def parse_shop(self, response: Response, shop: dict) -> Iterable[Feature]:
        """Build the base Feature for a shop, then optionally fetch its detail page."""
        item = DictParser.parse(shop)
        item["lat"] = float(shop["lat"])
        item["lon"] = float(shop["lon"])
        for prepared in self.post_process_item(item, response, shop) or []:
            if self._is_parse_detail_page_overridden() and (website := prepared.get("website")):
                yield Request(url=website, callback=self.parse_detail, meta={"item": prepared, "feature": shop})
            else:
                yield prepared

    def _is_parse_detail_page_overridden(self) -> bool:
        """Whether the subclass overrode :meth:`parse_detail_page`, opting into detail fetching."""
        return type(self).parse_detail_page is not LocationSmartSpider.parse_detail_page

    def parse_detail(self, response: Response) -> Iterable[Feature]:
        """Fetch a shop's detail page and hand it to :meth:`parse_detail_page`."""
        item = response.meta["item"]
        feature = response.meta["feature"]
        yield from self.parse_detail_page(response, item, feature) or []

    def post_process_item(self, item: Feature, response: Response, source_feature: dict) -> Iterable[Feature]:
        """Override to add or adjust fields on the item."""
        yield item

    def parse_detail_page(self, response: Response, item: Feature, source_feature: dict) -> Iterable[Feature]:
        """Override to enrich the item from a per-store detail page."""
        yield item
