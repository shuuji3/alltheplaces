import csv
from io import StringIO
from urllib.parse import urlencode

from chompjs import parse_js_object
from scrapy import FormRequest, Spider

from locations.categories import Categories, apply_category
from locations.geo import city_locations, country_iseadgg_centroids
from locations.items import Feature

MAX_ITEMS = 1640  # determined experimentally
RADIUS_KM = 24
MAP_ID = "search"


class JapanPostJPSpider(Spider):
    name = "japan_post_jp"

    def make_request(self, lat, lon, radius, offset=1, count=900):
        params = {
            "cid": MAP_ID,
            "postcid": "searchPO",
            "search_tempo": "1",
            "search_post": "1",
            "opt": "search",
            "pos": offset,
            "cnt": count,
            "enc": "EUC",
            "lat": lat,
            "lon": lon,
            "knsu": MAX_ITEMS,
            "postknsu": MAX_ITEMS,
            "rad": radius,
            "hour": 1,
        }
        target = f"http://127.0.0.1/cgi/nkyoten.cgi?{urlencode(params)}"
        return FormRequest(
            f"https://map.japanpost.jp/p/{MAP_ID}/zdcemaphttp.cgi?zdccnt=1&enc=EUC",
            formdata={"target": target},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://map.japanpost.jp/p/search/nmap.htm",
            },
            cb_kwargs={"lat": lat, "lon": lon, "offset": offset},
        )

    async def start(self):
        radius_m = RADIUS_KM * 1000
        for lat, lon in country_iseadgg_centroids("JP", RADIUS_KM):
            yield self.make_request(lat, lon, radius_m)
        for city in city_locations("JP", 200000):
            yield self.make_request(city["latitude"], city["longitude"], 5500)

    def parse(self, response, lat, lon, offset):
        # response is an EUC-encoded JS file that looks like
        #   ZdcEmapHttpResult[1] = '...';
        # where the string body is a TSV
        js_body = response.body.decode("euc-jp")
        # chompjs sees the array index as an array itself, so get just the string itself:
        js_str = js_body[js_body.find("'") : js_body.rfind("'") + 1]
        # For some reason, neither Python json nor chompjs like just the string on its own, so wrap it in an array
        js_ls = f"[{js_str}]"
        (tsv_str,) = parse_js_object(js_ls)
        reader = csv.reader(StringIO(tsv_str), delimiter="\t")
        ret_code, rec_count, hit_count = map(int, next(reader))
        assert rec_count <= hit_count, (rec_count, hit_count)
        if hit_count >= MAX_ITEMS:
            self.logger.warning("Maximum number of items returned in one query, consider lowering the radius")
        if rec_count >= hit_count:
            yield self.make_request(lat, lon, offset + rec_count)
        for row in reader:
            if row[0] == "POST":
                item = Feature()
                item["ref"] = row[1]
                item["website"] = f"https://map.japanpost.jp/p/{MAP_ID}/dtl/{row[1]}/?post=1"
                item["lat"] = row[2]
                item["lon"] = row[3]
                item["postcode"] = row[21]
                item["addr_full"] = row[7]
                apply_category(Categories.POST_BOX, item)
                item["name"] = "ポスト"
                yield item
                continue

            if row[4] == "99":
                continue

            item = Feature()
            item["ref"] = row[1]
            item["website"] = f"https://map.japanpost.jp/p/{MAP_ID}/dtl/{row[1]}/"
            item["lat"] = row[2]
            item["lon"] = row[3]
            item["postcode"] = row[13]
            item["addr_full"] = row[14]
            # col [4] is an icon_id (marker image) that selects the category:
            #   01, 02          = post office
            #   03,04,06,07,08  = ATM
            #   05              = Japan Post Insurance
            #   99              = search-center pin, not a real location
            if row[4] in ("01", "02"):
                apply_category(Categories.POST_OFFICE, item)
                item.update({"brand": "日本郵便", "brand_wikidata": "Q11509260"})
                item["name"] = row[7]
            elif row[4] == "05":
                apply_category(Categories.OFFICE_INSURANCE, item)
                item.update({"brand": "かんぽ生命保険", "brand_wikidata": "Q6157781"})
                item["name"] = row[7]
            else:
                apply_category(Categories.ATM, item)
                item.update({"brand": "ゆうちょ銀行", "brand_wikidata": "Q907103"})
                item["branch"] = row[7].removesuffix("出張所")

            yield item
