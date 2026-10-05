# 宣成社 紹介動画（senseisha_pv.mp4）のソース

- `crop.py` … PDFページ画像から素材写真を切り出し
- `script.json` / `tts.py` … ナレーション台本とVOICEVOX（No.7）での音声生成
- `bgm.py` … BGMの自動生成
- `index.html` … GSAPによるアニメーション本体（1920×1080）
- `subs.json` / `build.py` … 字幕・タイミングを埋め込み render.html を作成
- `render.js` … Playwrightで1/30秒ずつ撮影し ffmpeg でMP4化

※ 素材画像・音声モデル・node_modules はリポジトリに含めていません。
クレジット表記：VOICEVOX:No.7
