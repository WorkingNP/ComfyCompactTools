# ExecPlan: <短い題名>
- Date: YYYY-MM-DD
- Owner: <あなた/担当>
- Status: Draft | Approved | In Progress | Done
- Related: <issue/PR/メモリンク>

## 1. 背景 / 問題
- 何が困っているか（ユーザー視点）
- 再現手順（UI操作 / API呼び出し）
- 現状仕様（該当ファイル/関数/エンドポイント）

## 2. ゴール（Goals）
- [ ] ゴール1（測定可能に）
- [ ] ゴール2

## 3. 非ゴール（Non-goals）
- 今回やらないこと（スコープ膨張防止）

## 4. 影響範囲（Touch points）
### UI
- web/app.js: <関数名・変更点>
- web/styles.css: <クラス名・変更点>

### Server / API
- server/: <対象モジュール>
- 触るエンドポイント:
  - /api/workflows
  - /api/workflows/{id}
  - /api/workflows/reload
  - /api/jobs
  - /api/jobs/{id}
  - /api/config（必要なら）

### Workflows（データ駆動）
- workflows/<workflow_id>/manifest.json
- workflows/<workflow_id>/template_api.json

### MCP（Phase6）
- tools: workflows_list / workflow_get / images_generate / images_generate_many

## 5. 方式（Approach）
「A案/B案」みたいに分岐がある場合はここで決める。
- 選定: A or B
- 理由: なぜそれが最小変更で安全か

## 6. 実装フェーズ（必ず“小さく”）
### Phase 0: 調査（Read only）
- [ ] 既存実装の確認（対象ファイルの読み取り）
- [ ] 既存の同類パターンを特定（コピペ元）
- 成果物: 「どこをどう変えるか」確定メモ

### Phase 1: テスト（RED）※ここを先に書く
> tdd-guideの方針に従い、テストを先に追加する。  
> 可能ならユニット/インテグレーション、UIはE2Eで守る。

- Unit:
  - [ ] server/tests/... 追加（Fake clientで通る）
  - [ ] 期待値: <具体的assert>

- Integration（可能なら）:
  - [ ] Cockpit APIとの結合部（requests client）を最小で検証

- E2E（重要UI変更がある場合は必須）:
  - [ ] e2e-runnerでユーザージャーニーを追加
  - [ ] 成果物: スクショ/trace/動画（失敗時）

### Phase 2: 実装（GREEN）
- [ ] 変更1（ファイル/関数）
- [ ] 変更2
- ルール: ここではテストを通すための最小実装に寄せる

### Phase 3: リファクタ（REFACTOR）
- [ ] 重複排除 / 命名 / ガード節
- [ ] 既存挙動の互換性維持（レガシーモードなど）

### Phase 4: 仕上げ
- [ ] README更新（必要なら）
- [ ] manifest/params の制約(min/max/choices)整備
- [ ] エラー時のメッセージ確認

## 7. DoD（完成条件）※ゲートとして使う
### Bronze（UI/APIで使える）
- [ ] UIで期待通り表示/操作できる
- [ ] POST /api/jobs → GET /api/jobs/{id} が成立
- [ ] Gallery / rerun 等の主要導線が壊れてない

### Silver（MCP経由で使える）
- [ ] workflows_list に出る
- [ ] workflow_get でschemaが正しい
- [ ] images_generate でURLが返る

### Gold（運用耐性）
- [ ] not e2e テストが緑
- [ ] E2Eが緑（フレーク対策込み）
- [ ] ドキュメント更新済み

## 8. リスクと対策
- リスク: <例: ws更新でギャラリーが反映されない>
  - 対策: <例: asset_new時のrender条件>

## 9. ロールバック / 安全策
- 失敗したら戻す手順
- feature flag / 分岐（あるなら）

## 10. Plan closure（最後に必ず畳む）
- Done:
  - [ ] ...
- Blocked:
  - [ ] ...（1文理由 + 次に聞くべき質問）
- Cancelled:
  - [ ] ...（理由）
