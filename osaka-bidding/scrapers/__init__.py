from scrapers.osaka_city import OsakaCityConstructionScraper, OsakaCityGoodsScraper
from scrapers.osaka_pref import OsakaPrefScraper

# 実装済みスクレイパー。ここに追加していく。
ALL_SCRAPERS = [
    OsakaPrefScraper(),
    OsakaCityConstructionScraper(),
    OsakaCityGoodsScraper(),
]

# 対象自治体の全体像（実装状況のトラッキング用）。
# True = ALL_SCRAPERS に実装済み, False = 未実装（TODO）
TARGET_MUNICIPALITIES = {
    "大阪府": True,
    "大阪市": True,
    "堺市": False,
    "岸和田市": False,
    "豊中市": False,
    "池田市": False,
    "吹田市": False,
    "泉大津市": False,
    "高槻市": False,
    "貝塚市": False,
    "守口市": False,
    "枚方市": False,
    "茨木市": False,
    "八尾市": False,
    "泉佐野市": False,
    "富田林市": False,
    "寝屋川市": False,
    "松原市": False,
    "大東市": False,
    "和泉市": False,
    "箕面市": False,
    "柏原市": False,
    "門真市": False,
    "藤井寺市": False,
    "東大阪市": False,
    "四條畷市": False,
    "交野市": False,
    "阪南市": False,
    "能勢町": False,
    "岬町": False,
}
