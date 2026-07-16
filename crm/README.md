# 売上・顧客管理システム

社内向けの簡易的な売上・顧客管理システムです。Flask + SQLite で構築しています。

## 機能

- ダッシュボード: 顧客数・売上件数・売上合計・今月の売上・最近の売上一覧
- 顧客管理: 一覧・新規登録・編集・削除
- 顧客詳細: 顧客ごとの売上履歴と累計売上
- 売上管理: 一覧・新規登録・編集・削除（ステータス: 見込み / 受注 / 請求済み / 入金済み）

## セットアップ

```bash
cd crm
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

`http://localhost:5000` にアクセスすると利用できます。初回起動時に `customers.db`（SQLite）が自動生成されます。
