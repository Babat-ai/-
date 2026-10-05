# index.html の写真を埋め込んで、1ファイルで持ち運べる slideshow.html を作る
import base64, re, pathlib

here = pathlib.Path(__file__).parent
html = (here / "index.html").read_text(encoding="utf-8")

def inline(match):
    data = base64.b64encode((here / match.group(0)).read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"

html = re.sub(r"photos/\d+\.jpg", inline, html)
(here / "slideshow.html").write_text(html, encoding="utf-8")
print("slideshow.html を作成しました")
