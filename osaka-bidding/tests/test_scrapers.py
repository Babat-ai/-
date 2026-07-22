from pathlib import Path

from bs4 import BeautifulSoup

from scrapers.base import TableListScraper, normalize_date

FIXTURE = Path(__file__).parent / "fixtures" / "sample_list.html"


class DummyScraper(TableListScraper):
    municipality = "テスト市"
    category = "工事"
    list_url = "https://example.osaka.jp/koukoku/index.html"


def test_normalize_date_handles_kanji_and_slash_formats():
    assert normalize_date("2026年7月20日 公告") == "2026-07-20"
    assert normalize_date("2026/7/21") == "2026-07-21"
    assert normalize_date("日付不明") == ""


def test_table_list_scraper_parses_rows_with_links():
    soup = BeautifulSoup(FIXTURE.read_text(), "html.parser")
    items = DummyScraper().parse(soup)

    assert len(items) == 2
    assert items[0].title == "○○道路改修工事"
    assert items[0].url == "https://example.osaka.jp/koukoku/001.html"
    assert items[0].announced_date == "2026-07-20"
    assert items[0].municipality == "テスト市"
    assert items[0].category == "工事"

    assert items[1].title == "△△庁舎清掃業務委託"
    assert items[1].announced_date == "2026-07-21"


def test_table_list_scraper_skips_rows_without_links():
    soup = BeautifulSoup(FIXTURE.read_text(), "html.parser")
    items = DummyScraper().parse(soup)
    titles = [item.title for item in items]
    assert "リンクなしの行" not in titles
