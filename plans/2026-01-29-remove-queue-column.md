# ExecPlan: Queue列撤去 + WS jobイベント停止
- Date: 2026-01-29
- Owner: codex
- Status: Draft
- Related: Chrome freeze / WS負荷

## 1. Context / Problem
- Queue列は大量ジョブ/進捗イベントでDOM更新が頻発し、Chromeが固まりやすい。
- ComfyUI本体はキュー更新頻度が低く、UI負荷が小さい。

## 2. Goals
- [ ] 画面中央のQueue列を撤去（表示なし）。
- [ ] WSのjob系イベントを既定で送らない（進捗・ジョブ更新停止）。
- [ ] 画像ビューの表示（プロンプト/設定メタ）は維持。

## 3. Non-goals
- ワークフローやMCP APIの変更
- ギャラリー仕様の変更（手動更新は維持）

## 4. Touch points
### UI
- web/index.html
- web/styles.css
- web/app.js

### Server
- server/events.py
- server/main.py

### Tests
- server/tests/test_ws_prefs.py

## 5. Approach
- Queue列（pane--mid）をHTMLから削除し、レイアウトを2カラム化。
- renderQueueは要素なしならno-op化。
- WS prefsの既定値を jobs=false / job_progress=false に変更。
- websocket接続時のjobs_snapshot送信をprefsに従って抑制。

## 6. Phases
### Phase 1: Tests (RED)
- [ ] DEFAULT_WS_PREFS が jobs/job_progress false を許容する
- [ ] event_allowed が jobs/job_progress=false で該当イベントを遮断

### Phase 2: Implement (GREEN)
- [ ] Queue列削除 + 2カラムレイアウト
- [ ] WS prefs既定値更新 + snapshot送信条件分岐
- [ ] renderQueueのno-op化

### Phase 3: Refactor
- [ ] UI側の不要な参照を整理

## 7. DoD
### Bronze
- [ ] Queue列が表示されない
- [ ] job系WSイベントが既定で送られない
- [ ] 画像ビューのメタ情報表示が維持される

### Silver
- [ ] WS prefsでjobsを再有効化可能

### Gold
- [ ] テストが通る
