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

---

## データ取得: yfinance

最新の株価・指標を取得するためにyfinanceを使う。

**セットアップ**: `pip install yfinance --break-system-packages`

**銘柄コード**: 日本株は末尾に `.T`（例: `7203.T`）

```python
import yfinance as yf

t = yf.Ticker("{証券コード}.T")
info = t.info

current_price  = info.get("currentPrice")
trailing_pe    = info.get("trailingPE")
forward_pe     = info.get("forwardPE")
pb_ratio       = info.get("priceToBook")
roe            = info.get("returnOnEquity")  # 小数（0.10 = 10%）
market_cap     = info.get("marketCap")
```

---

## 実行フロー

### 1. ナレッジの読み込み
Notion MCP でファンダメンタルズ指標リファレンス（32c5e790-da82-816a-b3cf-d40b2045f418）を読み、割安判定のチェックフローと指標基準を把握する。

### 2. 銘柄リストの取得
Notion MCP で銘柄リサーチDB（collection://005de437-7b9d-46cf-8bcd-827d8c52b999）から全銘柄を取得する。

### 3. 最新指標の取得
yfinanceで各銘柄のPER/PBR/ROE/自己資本比率/現在株価を取得する。

### 4. 割安判定
ファンダメンタルズ指標リファレンスのチェックフローに従って各銘柄を判定する（割安/やや割安/妥当/割高）。

割安またはやや割安の銘柄については、ウェブ検索で「なぜ割安なのか」を調査する:
- 一時的な悪材料（悪材料出尽くし、市場全体の下落等）→ チャンスの可能性
- 構造的な問題（業界衰退、競争力低下等）→ 割安の罠の可能性

全銘柄にコメントをつける（割安なものは手厚く、妥当/割高は一言）。

### 5. Notionに書き戻し
銘柄リサーチDBの各銘柄を更新する:
- PER, PBR, ROE, 自己資本比率 → 最新の数値
- 割安判定 → 判定結果
- 調査日 → 今日の日付

### 6. LINE通知

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