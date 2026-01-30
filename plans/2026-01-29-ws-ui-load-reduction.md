# ExecPlan: WS負荷削減 + Queue軽量化
- Date: 2026-01-29
- Owner: codex
- Status: Draft
- Related: UI freeze / Chrome heavy

## 1. Context / Problem
- WSイベント（特にjob_progress）が高頻度で流れ、毎回Queue再描画が走ってChromeが固まる。
- ComfyUI本体は1ジョブ内の進捗だけを見るため、更新頻度が低くUI負荷が小さい。

## 2. Goals
- [ ] job_progressを既定で無効化し、WSイベント量を削減する。
- [ ] Queueの描画対象を最新N件に制限してDOM更新量を削減する。
- [ ] 既存機能は維持（進捗を見たい場合は再有効化可能）。

## 3. Non-goals
- ワークフローやMCP APIの変更
- ギャラリーの仕様変更（手動更新は現状維持）

## 4. Touch points
### UI
- web/app.js

### Server
- server/events.py
- server/main.py

### Tests
- server/tests/test_ws_prefs.py（新規）

## 5. Approach
- WSの受信側で「送信フィルタ」を導入し、client prefsでjob_progressを抑制。
- UIは接続時に`{job_progress:false}`を送る。
- Queueは最新N件のみ描画（既定50）。

## 6. Phases
### Phase 1: Tests (RED)
- [ ] event_allowed() が prefs に従って job_progress を遮断する
- [ ] normalize_ws_prefs() が未知キーを無視し既知キーのみ更新する

### Phase 2: Implement (GREEN)
- [ ] events.py に prefs と event_allowed を追加
- [ ] websocket_endpoint で prefs 更新を受け付け
- [ ] app.js で prefs を送信 + job_progress 無視
- [ ] Queueの描画件数を制限

### Phase 3: Refactor
- [ ] 余分な分岐や不要な更新の整理

## 7. DoD
### Bronze
- [ ] job_progressが既定で止まり、Queue更新頻度が下がる
- [ ] Queueが最新N件のみ表示される

### Silver
- [ ] prefsでjob_progressを再有効化できる

### Gold
- [ ] テストが全て通る
