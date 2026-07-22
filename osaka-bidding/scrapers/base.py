import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from models import BidItem

logger = logging.getLogger(__name__)

USER_AGENT = (
    "OsakaBiddingWatcher/1.0 "
    "(+https://github.com/babat-ai/-; 個人利用の入札情報収集bot。問題があればリポジトリのissueへ連絡ください)"
)

REQUEST_TIMEOUT = 20

# 全角/半角が混在する日付表記をゆるく拾うための正規表現（例: 2026年7月22日, 2026/7/22, 2026-07-22）
DATE_PATTERN = re.compile(r"(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})")


def normalize_date(text: str) -> str:
    """日本語日付表記っぽい文字列から YYYY-MM-DD を抜き出す。見つからなければ空文字。"""
    if not text:
        return ""
    m = DATE_PATTERN.search(text)
    if not m:
        return ""
    year, month, day = (int(g) for g in m.groups())
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return ""


class BaseScraper(ABC):
    municipality: str = ""

    def get_soup(self, url: str) -> BeautifulSoup:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")

    @abstractmethod
    def fetch(self) -> list[BidItem]:
        """公告一覧を取得して BidItem のリストで返す。取得失敗時は例外を送出してよい
        （呼び出し側の fetch_all.py が1自治体の失敗を他自治体に波及させない）。"""
        raise NotImplementedError


class TableListScraper(BaseScraper):
    """多くの自治体サイトで使われる「表形式の公告一覧」向けの汎用スクレイパー。

    ページ内の <table> を走査し、各行から最初のリンクをタイトル/URLとして、
    行内のテキストから日付らしき文字列を公告日として拾う。
    サイトごとに癖があるため、うまく拾えない場合はサブクラスで fetch() を
    オーバーライドして個別に実装すること。
    """

    list_url: str = ""
    category: str = ""

    def fetch(self) -> list[BidItem]:
        soup = self.get_soup(self.list_url)
        return self.parse(soup)

    def parse(self, soup: BeautifulSoup) -> list[BidItem]:
        """HTMLパース部分だけを切り出したもの（ネットワーク不要でテストできるように）。"""
        items: list[BidItem] = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                link = row.find("a", href=True)
                if link is None:
                    continue
                title = link.get_text(strip=True)
                if not title:
                    continue
                href = requests.compat.urljoin(self.list_url, link["href"])
                row_text = row.get_text(" ", strip=True)
                announced_date = normalize_date(row_text)
                items.append(
                    BidItem(
                        municipality=self.municipality,
                        source_id=href,
                        title=title,
                        url=href,
                        category=self.category,
                        announced_date=announced_date,
                    )
                )
        return items
