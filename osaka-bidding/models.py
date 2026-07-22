from dataclasses import dataclass


@dataclass
class BidItem:
    """1件の入札公告を表す共通データモデル。"""

    municipality: str  # 自治体名（例: "大阪府", "大阪市"）
    source_id: str  # 発注機関内で一意な案件ID（同一案件の再取得を検知するためのキー）
    title: str  # 案件名
    url: str  # 詳細ページ or 公告PDFのURL
    category: str = ""  # 工事 / 物品 / 委託 など
    announced_date: str = ""  # 公告日（YYYY-MM-DD、取得できない場合は空文字）
    deadline: str = ""  # 入札・申込等の締切（YYYY-MM-DD、取得できない場合は空文字）
