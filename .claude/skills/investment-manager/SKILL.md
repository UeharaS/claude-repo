---
name: investment-manager
description: "週次の銘柄レーティング更新・割安判定を実行するスキル。"
---

# Investment Manager

週次で銘柄リサーチDBの全銘柄に対してレーティング更新・割安判定を行い、結果をNotionに書き戻してLINE通知する。

---

## Notionリソース

| リソース | ID | 用途 |
|---|---|---|
| ファンダメンタルズ指標リファレンス | 32c5e790-da82-816a-b3cf-d40b2045f418 | 割安判定のチェックフローと指標基準 |
| 投資ルール | 32c5e790-da82-81c5-af23-c044d339234d | 損切り/利確ライン等の投資方針 |
| 銘柄リサーチDB | collection://005de437-7b9d-46cf-8bcd-827d8c52b999 | 銘柄一覧と指標値の永続化 |
| 仮説カードDB | collection://3305e790-da82-80d8-91ad-000b055d0385 | 仮説との関連判定に使用 |
| ニュースログDB | data_source_id: b94982fa-82c8-4360-9a93-a8215f15f629 | 今週のトレンド・個別銘柄ニュースの参照 |

---

## データ取得: fetch_indicators.py

最新の株価・指標の取得には `scripts/fetch_indicators.py` を使う。
yfinanceのインストール、異常値検知、欠損値のフォールバック計算をすべてスクリプト内で処理する。

**実行方法:**
```bash
python scripts/fetch_indicators.py '[{"code":"6701","name":"NEC"},{"code":"9432","name":"NTT"}]'
```

**入力:** 銘柄リスト（JSON配列。各要素に `code`（証券コード）と `name`（銘柄名）が必要）

**出力:** JSON配列。各銘柄ごとに以下のフィールドを返す:
- `status`: ok / not_found / error
- `current_price`: 現在株価
- `per`: PER（異常値除外済み。trailing優先、異常時はforward採用）
- `per_source`: trailing / forward / unavailable
- `pbr`: PBR
- `roe`: ROE（%表記。infoで取れなければbalance_sheet+financialsから計算）
- `equity_ratio`: 自己資本比率（%表記。balance_sheetから計算）
- `market_cap`: 時価総額

**スクリプトが処理する異常値ルール:**
- PER < 0.01 または > 500 → 除外してフォールバック
- ROE null → balance_sheet + financials から計算
- 自己資本比率 → 常に balance_sheet から計算（info は信頼性が低い）
- ティッカー404 → status: not_found を返す（LINE通知に注記すること）

---

## 実行フロー

### 1. ナレッジの読み込み
Notion MCP でファンダメンタルズ指標リファレンス（32c5e790-da82-816a-b3cf-d40b2045f418）を読み、割安判定のチェックフローと指標基準を把握する。

### 2. 銘柄リストの取得
Notion MCP で銘柄リサーチDB（collection://005de437-7b9d-46cf-8bcd-827d8c52b999）から全銘柄を取得する。page_size=25で足りない場合はページネーションして全件取得すること。

### 3. 今週のニュースログの読み込み
Notion MCP でニュースログDB（data_source_id: b94982fa-82c8-4360-9a93-a8215f15f629）から、直近1週間分のトレンドニュースと個別銘柄ニュースを取得する。割安判定やコメント作成時の材料として使う。

### 4. 仮説カードの読み込み
Notion MCP で仮説カードDB（collection://3305e790-da82-80d8-91ad-000b055d0385）から全仮説を取得し、詳細ページを読む。

### 5. 最新指標の取得
Step 2で取得した銘柄リストから証券コードと銘柄名のJSON配列を作り、`scripts/fetch_indicators.py` を実行する。
出力JSONのstatusが not_found や error の銘柄は割安判定からスキップし、LINE通知に注記する。

### 6. 割安判定
ファンダメンタルズ指標リファレンスのチェックフローに従って各銘柄を判定する（割安/やや割安/妥当/割高）。

割安またはやや割安の銘柄については、ウェブ検索で「なぜ割安なのか」を調査する:
- 一時的な悪材料（悪材料出尽くし、市場全体の下落等）→ チャンスの可能性
- 構造的な問題（業界衰退、競争力低下等）→ 割安の罠の可能性

今週のニュースログも判断材料に加える:
- トレンドニュースで仮説を支持/脅かす動きがあったか
- 個別銘柄ニュースで業績やIRに変化があったか
- これらを踏まえてコメントに反映する

全銘柄にコメントをつける（割安なものは手厚く、妥当/割高は一言）。

### 7. Notionに書き戻し
銘柄リサーチDBの各銘柄を更新する:
- PER, PBR, ROE, 自己資本比率 → 最新の数値
- 割安判定 → 判定結果
- 調査日 → 今日の日付

### 8. LINE通知

```bash
curl -X POST https://api.line.me/v2/bot/message/push \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN" \
  -d '{
    "to": "'"$LINE_USER_ID"'",
    "messages": [{"type": "text", "text": "（通知メッセージ）"}]
  }'
```

**通知フォーマット:**

【週次レーティング更新】

■ 割安（買い検討候補）
銘柄名（証券コード）PER:○ PBR:○ ROE:○%
理由: なぜ割安か（一時的/構造的）
コメント: 総合的な所感、今後の注目ポイント

■ やや割安
銘柄名（証券コード）PER:○ PBR:○ ROE:○%
理由: なぜ割安か
コメント: 所感

■ 妥当
銘柄名（証券コード）
コメント: 一言（前週から変化があれば触れる）

■ 割高
銘柄名（証券コード）
コメント: 一言

---

## 注意事項

- 環境変数(Line-env) LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を使用すること
- 日付はJST基準
- Claudeは金融アドバイザーではない。投資の最終判断はユーザーが行う