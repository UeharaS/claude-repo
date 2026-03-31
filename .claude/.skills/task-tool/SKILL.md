---
name: task-tool
description: "タスクのライフサイクルを一元管理するスキル。タスクの作成・編集・完了・一覧確認・スケジューリング（カレンダーへのブロッキング配置）を行う。ユーザーが「タスク追加して」「タスク完了にして」「やること確認して」「タスクをスケジュールして」「未完了タスク整理して」「今週やること入れて」「タスクいつやる？」など、タスクに関する操作や質問をしたときに必ずこのスキルを使う。タスク、TODO、やること、完了、未完了、スケジュール、ブロッキングといったキーワードが出てきたらこのスキルの出番。予定・カレンダーの直接操作（予定の確認・作成等）はschedule-toolが担当。Notionへの汎用操作（PJ作成・ワークスペース管理）はnotion-workspace-managerが担当。"
---

# Task Tool

タスクのライフサイクルを一元管理するスキル。Notion Task DBをデータストアとし、必要に応じてschedule-toolとnotion-workspace-managerを内部的に利用する。

**ナレッジページID:** `3325e790da82818982a2ddced3aee087`

---

## 依存スキル

| スキル | 用途 |
|--------|------|
| notion-workspace-manager | Task DBへの読み書き（Notionの汎用操作レイヤー） |
| schedule-tool | カレンダーへの予定登録・空き時間検索 |

タスクのドメインロジック（何を・いつ・どう管理するか）はこのスキルが持つ。NotionやカレンダーのAPI操作は各依存スキルに委譲する。

---

## Task DBの基本情報

- data_source: `collection://3255e790-da82-8020-b502-000b2746b4be`
- data_source_id: `3255e790-da82-8020-b502-000b2746b4be`

### プロパティ

| プロパティ | 型 | 説明 |
|-----------|-----|------|
| name | title | タスク名 |
| status | select | ToDo / Done |
| deadline | date | 期限（いつまでにやるか） |
| scheduled | date | 実施日（いつやるか。カレンダーにブロッキングする日時） |
| frequency | select | なし / 毎日 / 毎週 / 毎月 |

---

## ユースケース

### 1. タスクの作成

notion-workspace-managerのタスク作成手順に従ってTask DBにレコードを追加し、必ずカレンダーにも登録する。

**プロパティの設定ルール:**
- name: タスク名
- status: デフォルトは「ToDo」
- deadline: 指示がなければ1ヶ月先
- scheduled: 必須。以下のルールで決定する
- frequency: 指示がなければ「なし」（単発タスク）

**scheduledの決定 → カレンダー登録（必ずセットで行う）:**

**Notion参照:** notion-fetch → ナレッジページ（`3325e790da82818982a2ddced3aee087`）の「スケジューリングルール」「カレンダー登録ルール」セクション

- まずナレッジページからスケジューリングルールとカレンダー登録ルールを取得する
- ユーザーが日付を指定した場合: その日をscheduledに設定し、schedule-toolでカレンダーに登録
- ユーザーが日付を指定しなかった場合: schedule-toolで空き時間を検索し、スケジューリングルールに従って日時を決定。scheduledに書き込み、カレンダーに登録

### 2. タスクの編集

notion-searchでタスクを検索し、notion-update-pageでプロパティを更新する。

### 3. タスクの完了

**単発タスク（frequency=なし）:**
statusを「Done」にして終了。

**定常タスク（frequency=なし以外）:**
Done にはせず、以下のリセットを行う:
1. statusは「ToDo」のまま
2. deadlineをfrequencyに応じて次の周期に進める
   - 毎日: +1日
   - 毎週: +7日
   - 毎月: +1ヶ月（翌月の同日）
3. ユーザーに「完了。次のdeadlineは○/○に設定したよ」と報告

### 4. タスク一覧の確認

notion-searchでTask DBからToDoタスクを取得し、一覧表示する。

### 5. タスクのスケジューリング（カレンダーブロッキング）

**Notion参照:** notion-fetch → ナレッジページ（`3325e790da82818982a2ddced3aee087`）の「スケジューリングルール」セクション

手順:
1. ナレッジページからタスクスケジューリングルールを取得
2. schedule-toolを使ってカレンダーの空き時間を検索
3. スケジューリングルールに従い、各タスクの実施日時を決定
4. 決定した実施日をNotion Task DBのscheduledプロパティに書き戻し
5 schedule-toolを使ってカレンダーに登録
6 期限が過ぎたタスクの削除

---

## スキルの責任範囲

| 操作 | 担当 |
|------|------|
| タスクの作成・編集・完了 | task-tool（このスキル） |
| タスク一覧の確認 | task-tool（このスキル） |
| タスクのスケジューリング判断 | task-tool（このスキル） |
| Notion Task DBへの読み書き | notion-workspace-manager経由 |
| カレンダーへの予定登録・空き時間検索 | schedule-tool経由 |
| カレンダー予定の直接操作（タスク以外） | schedule-tool |
| PJ・ワークスペース管理 | notion-workspace-manager |
| リマインド管理 | notion-remind-manager |

---

## 注意事項

- タスクのドメインルール（スケジューリングルール、未完了判定、再スケジューリング方針）はNotionのナレッジページが正。SKILL.mdにはドメインルールのコピーを持たない
- カレンダーに登録する際のカラールール（colorId=2=Sage）や予定名ルール（タスク名をそのままsummary、時間表記不要）はschedule-toolのナレッジを参照