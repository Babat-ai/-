# なびメイト 紹介動画（navimate_manual.mp4）のソース

マニュアル（pptx・35枚）を、案内係キャラクター「ミサキ」が説明する約4分47秒の動画にしたものです。

- `script.json` … ナレーション台本（字幕 `s` と読み上げ用 `t` を分けられる）
- `tts.py` … VOICEVOX（No.7 ノーマル）で音声を生成し、タイミングと口パク用データ（voice/timeline.json）を作成
- `character.svg.html` … キャラクター「ミサキ」（SVG）。まばたき・口パク・うなずき・腕のジェスチャーは index.html 側で動かす
- `index.html` … GSAPによるアニメーション本体（1920×1080）。画面紹介シーンは `SCR` の設定（画像・ズーム位置・ポイント）で作る
- `bgm.py` … BGMの自動生成（チャプター切り替えに合わせてブレイク・効果音を入れる）
- `build.py` … タイムラインとキャラクターを埋め込んで render.html を作成
- `render.js` … Playwrightで1/30秒ずつ撮影し ffmpeg でMP4化（`node render.js 0 4` 〜 `3 4` で並列）

※ 素材画像（img/ … pptxから切り出したスクリーンショット）・音声モデル・node_modules はリポジトリに含めていません。
クレジット表記：VOICEVOX:No.7
