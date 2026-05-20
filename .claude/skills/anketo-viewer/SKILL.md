---
name: anketo-viewer
description: 振り返りアンケートDBの「閲覧」プロパティに、「メンバー」リレーション先と同じ人を自動入力する。新規回答が増えたタイミングで使う。
disable-model-invocation: false
allowed-tools: Bash, Read
---

# 振り返りアンケート 閲覧者埋めスキル

neoAIの「振り返りアンケート」DBで、「閲覧」が空かつ「メンバー」リレーションが入っている行に対し、メンバー本人を閲覧者として設定する。

## 接続情報

- `.env` の `NOTION_TOKEN`（社内Integration）を使う
- 振り返りアンケート DB: `2fb26386566780ac9fa8e816ce785762`
- Members DB: `2b979997-a4c4-4a13-ac5c-fa638306f329`
- Members DBの `ユーザー` (people型) プロパティから user_id を引く（`/users` API は範囲制限あるので使わない）

## 実行手順

1. **ドライランで件数確認**
   ```bash
   cd /Users/shomauehara/work/claude-workspace
   export $(grep -E '^NOTION_TOKEN=' .env | xargs)
   DRY_RUN=1 python3 .claude/skills/anketo-viewer/fill_viewer.py
   ```

2. **件数と未マッチを報告し、ユーザーに確認を取る**
   - 更新対象N件、未マッチM件 のサマリを見せる
   - 未マッチが出てるときは、Members DBの「ユーザー」プロパティが空 = 退職者の可能性が高い
   - 0件なら「更新対象なし」で終了

3. **実行**
   ```bash
   DRY_RUN=0 python3 .claude/skills/anketo-viewer/fill_viewer.py
   ```

## 動作仕様

- 対象: `メンバー`リレーションあり & `閲覧`が空 の行のみ（既存の閲覧は触らない）
- マッチング: 名前ベースではなく、Members DBの`ユーザー`(people)プロパティから直接 user_id を取得
- レート対策: 1リクエスト 0.35秒スリープ
- ユーザー紐付けがないMember（退職者等）はスキップしてログ出力

## 注意事項

- 書き換える前に必ず DRY_RUN=1 で確認
- 60件で約30秒。100件超なら数分かかる
- スクリプト本体: `.claude/skills/anketo-viewer/fill_viewer.py`
