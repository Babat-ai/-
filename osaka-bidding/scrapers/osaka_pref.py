# 大阪府: 建設工事の入札公告一覧
# NOTE: 開発環境からは大阪府サイトに直接アクセスできず、実際のHTML構造を目視確認できないまま
#       実装している（README「開発上の制約」参照）。GitHub Actions初回実行後、0件しか
#       取得できない場合はページ構造が想定と異なる可能性が高いので selector を要調整。
from scrapers.base import TableListScraper


class OsakaPrefScraper(TableListScraper):
    municipality = "大阪府"
    category = "建設工事"
    list_url = "https://www.pref.osaka.lg.jp/o040110/keiyaku_2/e-nyuusatsu/e-kensetsu-koukoku.html"
