# 大阪市: 契約管財局の入札情報（工事請負／物品供給等）
# NOTE: 大阪府と同様、実際のHTML構造は未検証（README「開発上の制約」参照）。
from scrapers.base import TableListScraper


class OsakaCityConstructionScraper(TableListScraper):
    municipality = "大阪市"
    category = "工事請負"
    list_url = "https://www.city.osaka.lg.jp/keiyakukanzai/category/3047-3-0-0-0-0-0-0-0-0.html"


class OsakaCityGoodsScraper(TableListScraper):
    municipality = "大阪市"
    category = "物品供給等"
    list_url = "https://www.city.osaka.lg.jp/keiyakukanzai/category/3047-4-0-0-0-0-0-0-0-0.html"
