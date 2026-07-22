# 大阪府 入札情報ウォッチャー

大阪府内の自治体の入札公告を毎日自動収集し、新着案件をメールでまとめて通知するシステムです。
収集した全案件は静的ダッシュボードでも閲覧できます。

## 仕組み

1. GitHub Actions が毎日 08:00 JST に起動（`.github/workflows/osaka-bidding.yml`）
2. `fetch_all.py` が各自治体のスクレイパー（`scrapers/`）を実行し、`data/bids.db`（SQLite）に保存。既知の案件は無視され、新規案件だけが検知される
3. `notify_email.py` が新規案件を自治体ごとにまとめてメール送信
4. `dashboard.py` が全案件の一覧を `docs/osaka-bidding/index.html` に静的HTMLとして生成
5. 更新された `data/bids.db` と `docs/osaka-bidding/` を bot がリポジトリにコミット

DBやダッシュボードはリポジトリにコミットして永続化する方式なので、常時稼働のサーバーは不要です。

## セットアップ

### 1. メール通知用の GitHub Secrets を設定

リポジトリの Settings → Secrets and variables → Actions で以下を登録してください。

| Secret名 | 内容 | 例 |
|---|---|---|
| `OSAKA_BIDDING_SMTP_HOST` | SMTPサーバー | `smtp.gmail.com` |
| `OSAKA_BIDDING_SMTP_PORT` | SMTPポート | `587` |
| `OSAKA_BIDDING_SMTP_USER` | SMTPユーザー名 | `bb1994612@gmail.com` |
| `OSAKA_BIDDING_SMTP_PASSWORD` | SMTPパスワード（Gmailの場合はアプリパスワード） | - |
| `OSAKA_BIDDING_MAIL_FROM` | 送信元アドレス（省略時はSMTPユーザーと同じ） | `bb1994612@gmail.com` |
| `OSAKA_BIDDING_MAIL_TO` | 送信先アドレス | `bb1994612@gmail.com` |

Gmailを使う場合は、通常のパスワードではなく「アプリパスワード」の発行が必要です（Googleアカウント設定 → セキュリティ → 2段階認証 → アプリパスワード）。

`OSAKA_BIDDING_SMTP_HOST` が未設定の間は、メール送信だけがスキップされ、データ収集とダッシュボード更新は通常どおり動作します。

### 2. ダッシュボードの公開（GitHub Pages）

このリポジトリの `docs/` フォルダは既に別のランディングページ用に使われているため、`docs/osaka-bidding/` というサブディレクトリに出力するようにしています。GitHub Pages が `docs/` を配信するよう設定済みであれば、追加設定なしで `https://<あなたのPagesドメイン>/osaka-bidding/` から閲覧できます。

Pages が未設定の場合は、Settings → Pages → Source を「Deploy from a branch」→ ブランチ `main` / フォルダ `/docs` に設定してください。

### 3. 手動実行・動作確認

```bash
cd osaka-bidding
pip install -r requirements.txt
python -m pytest tests/ -q   # ユニットテスト（実サイトへのアクセスなし）
python fetch_all.py          # スクレイピング＋DB保存
python notify_email.py       # 新着があればメール送信（SMTP環境変数が必要）
python dashboard.py          # ダッシュボード生成
```

GitHub上では Actions タブから `Osaka Bidding Watcher` を選び「Run workflow」で手動実行もできます。

## 開発上の制約（重要）

このシステムを実装したセッションのサンドボックス環境は、ネットワークポリシーにより外部サイトへのアクセスが広範囲にブロックされており（`example.com` のようなテストサイトすら遮断）、対象自治体サイトの実際のHTML構造を目視確認できませんでした。

そのため `scrapers/osaka_pref.py` と `scrapers/osaka_city.py` は、検索結果から判明したURLと、多くの自治体サイトで一般的な「表形式の一覧ページ」という想定（`scrapers/base.py` の `TableListScraper`）に基づいて実装しています。**実際のページ構造と一致しない可能性があります。**

初回のGitHub Actions実行後、以下を確認してください。

- Actionsのログで各スクレイパーの取得件数が0件になっていないか（`fetch_all.py` は自治体ごとの取得件数をログ出力します）
- 0件が続く、またはエラーになる場合は、該当ページのHTMLを確認し、`TableListScraper` の想定が合わない箇所（テーブル構造が違う、JavaScriptでレンダリングされている等）を特定して個別スクレイパーを修正してください

## 対象自治体・実装状況

大阪府（府発注案件）＋ 大阪府内29市町（`scrapers/__init__.py` の `TARGET_MUNICIPALITIES` で管理）。

| 自治体 | 状態 |
|---|---|
| 大阪府 | ✅ 実装済み（未検証、上記「開発上の制約」参照） |
| 大阪市 | ✅ 実装済み（未検証、上記「開発上の制約」参照） |
| 堺市 | ⬜ 未実装 |
| 岸和田市 | ⬜ 未実装 |
| 豊中市 | ⬜ 未実装 |
| 池田市 | ⬜ 未実装 |
| 吹田市 | ⬜ 未実装 |
| 泉大津市 | ⬜ 未実装 |
| 高槻市 | ⬜ 未実装 |
| 貝塚市 | ⬜ 未実装 |
| 守口市 | ⬜ 未実装 |
| 枚方市 | ⬜ 未実装 |
| 茨木市 | ⬜ 未実装 |
| 八尾市 | ⬜ 未実装 |
| 泉佐野市 | ⬜ 未実装 |
| 富田林市 | ⬜ 未実装 |
| 寝屋川市 | ⬜ 未実装 |
| 松原市 | ⬜ 未実装 |
| 大東市 | ⬜ 未実装 |
| 和泉市 | ⬜ 未実装 |
| 箕面市 | ⬜ 未実装 |
| 柏原市 | ⬜ 未実装 |
| 門真市 | ⬜ 未実装 |
| 藤井寺市 | ⬜ 未実装 |
| 東大阪市 | ⬜ 未実装 |
| 四條畷市 | ⬜ 未実装 |
| 交野市 | ⬜ 未実装 |
| 阪南市 | ⬜ 未実装 |
| 能勢町 | ⬜ 未実装 |
| 岬町 | ⬜ 未実装 |

なお、検索調査で「大阪地域市町村共同利用電子入札システム」（複数自治体が共同利用する電子入札プラットフォーム）の存在が分かりました。もし対象自治体の多くがこれを共通利用していれば、1つのスクレイパーで複数自治体をカバーできる可能性があります。未検証のため、自治体追加時に調査してみる価値があります。

## 自治体スクレイパーの追加方法

1. `scrapers/` に新しいファイルを作成し、`BaseScraper`（`scrapers/base.py`）を継承
2. 表形式の一覧ページなら `TableListScraper` を継承してURLを指定するだけで動く場合がある。動かない場合は `fetch()` を個別実装
3. `scrapers/__init__.py` の `ALL_SCRAPERS` に追加し、`TARGET_MUNICIPALITIES` の状態を `True` に更新
4. `tests/fixtures/` に対象ページのHTMLサンプルを保存し、`tests/test_scrapers.py` を参考にパース結果を検証するテストを追加
5. `robots.txt` を確認し、過度なアクセス頻度にならないよう注意（`fetch_all.py` は自治体間に2秒の間隔を空けています）

## ディレクトリ構成

```
osaka-bidding/
  models.py          # BidItem データモデル
  db.py               # SQLite保存・重複排除
  schema.sql          # DBスキーマ
  scrapers/
    base.py            # スクレイパー基底クラス・汎用テーブルパーサー
    osaka_pref.py       # 大阪府
    osaka_city.py        # 大阪市
    __init__.py           # スクレイパー登録・対象自治体一覧
  fetch_all.py        # 全自治体をスクレイピングしてDB保存
  notify_email.py     # 新着案件のメール通知
  dashboard.py         # 静的ダッシュボード生成
  data/bids.db          # 蓄積データ（リポジトリにコミット）
  tests/                  # ユニットテスト（ネットワーク不要）
```
