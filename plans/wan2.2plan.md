# ExecPlan: Wan2.2 TI2V i2v 追加（手動出力確認）
- Date: 2026-01-30
- Owner: souto
- Status: Draft
- Related: plans/_TEMPLATE.md

## 1. 背景 / 問題
- Wan2.2 の i2v（画像→動画）を manifest + template 方式で追加したい
- 現状の動的フォームはトップレベル送信のため、未知パラメータが JobCreate で切り捨てられる
- 動画出力は assets に取り込む仕組みがないため、今回は手動確認とする
- Workflow追加後に UI の一覧へ出てこないことがある（workflow_registry のキャッシュ）

## 2. ゴール（Goals）
- [ ] /api/workflows に `wan2_2_ti2v_5b` が出る
- [ ] /api/workflows/{id} が manifest を返し、params から動的フォームが生成される
- [ ] `prompt/negative_prompt/width/height/length/fps/steps/cfg/sampler/scheduler/seed/start_image` を params 経由で受け取れる
- [ ] start_image をアップロードして ComfyUI/input に保存できる
- [ ] 生成された動画は **ComfyUI output で手動確認**できる
- [ ] UIのWorkflow選択に `wan2_2_ti2v_5b` が表示される（必要なら /api/workflows/reload を叩く）
- [ ] `pytest -m "not e2e"` が緑

## 3. 非ゴール（Non-goals）
- v2v / fun control / 追加ワークフロー
- 動画の assets 取り込み、ギャラリー表示、UIでの再生
- 動画の自動品質検査（フレーム抽出など）

## 4. 影響範囲（Touch points）
### UI
- web/app.js: 画像入力（type=image）を file input に変換、params 送信を統一、必要なら workflows reload
- web/index.html / web/styles.css: 画像入力に必要な見た目調整（必要なら最小）

### Server / API
- server/main.py: JobCreate/params 正規化、/api/uploads/image 追加、入力ディレクトリ設定
- server/settings 相当: COMFY_INPUT_DIR（または COMFY_DIR から input を組み立て）
- server/fake_comfy_client.py: テスト用に入力受け取りの痕跡を確認

### Workflows（データ駆動）
- workflows/wan2_2_ti2v_5b/manifest.json
- workflows/wan2_2_ti2v_5b/template_api.json（公式テンプレを保存して使用）

### MCP（Phase6）
- tools: workflows_list / workflow_get / images_generate / images_generate_many

## 5. 方式（Approach）
- 選定: **params 統一方式**
- 理由: 既存スキーマを壊さず、安全性が高く、変更箇所が限定的
- 動画出力は assets 化せず、**ComfyUI output を手動で確認**する

## 6. 実装フェーズ（必ず“小さく”）
### Phase 0: 調査（Read only）
- [ ] 既存 manifest / patcher / UI 動的フォームの確認
- [ ] Wan2.2 TI2V 公式テンプレのノードIDを把握（patch対象を確定）
  - 公式テンプレ（参考にすること）: https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_wan2_2_5B_ti2v.json
- 成果物: patch対象ノード一覧

### Phase 1: テスト（RED）
- Unit:
  - [ ] /api/workflows に `wan2_2_ti2v_5b` が含まれる
  - [ ] /api/workflows/{id} の params に `start_image` (type=image) がある
  - [ ] patcher が length/fps/start_image などを正しく反映する
  - [ ] params で渡した追加項目が DB に保存される（切り捨てられない）
  - [ ] /api/uploads/image が multipart を保存し filename を返す

- Integration:
  - [ ] FakeComfyClient で submit prompt の組み立て確認

- E2E:
  - [ ] Agent Browser でUIを開き、Workflow選択に `wan2_2_ti2v_5b` が表示されることを確認（スクショ保存）
  - [ ] テスト画像はルートの `スクリーンショット 2026-01-27 161718.png` を使用
  - [ ] job 生成が開始されることを最低限確認
  - [ ] **動画の結果確認は手動**（ComfyUI output で確認）

### Phase 2: 実装（GREEN）
- [ ] wan2_2_ti2v_5b の workflow 追加（manifest + template）
- [ ] params 統一送信（UI/クライアント）
- [ ] /api/uploads/image 実装 + 保存先設定
- [ ] apply_patch 対象ノードの更新（manifest の patch 定義）
- [ ] UI 初期化時に /api/workflows/reload → /api/workflows の順で取得（キャッシュ対策）

### Phase 3: リファクタ（REFACTOR）
- [ ] params 正規化の重複を整理
- [ ] 既存 workflow への影響なしを確認

### Phase 4: 仕上げ
- [ ] README 更新（必要モデル・入力ディレクトリ・手動確認の明記）
- [ ] manifest の min/max/choices 整備

## 7. DoD（完成条件）
### Bronze
- [ ] UIで i2v ワークフローが選べる
- [ ] start_image を指定して /api/jobs が作成できる
- [ ] **ComfyUI output で動画を手動確認できる**

### Silver
- [ ] workflows_list に `wan2_2_ti2v_5b` が出る
- [ ] workflow_get で schema が正しい
- [ ] images_generate が job を作成できる（出力URLは不要）

### Gold
- [ ] `pytest -m "not e2e"` が緑
- [ ] E2E が最低限の job 作成まで緑
- [ ] README 更新済み

## 8. リスクと対策
- リスク: params が切り捨てられて workflow に反映されない
  - 対策: params 統一送信 + テストで固定
- リスク: start_image の保存先が ComfyUI input とズレる
  - 対策: COMFY_INPUT_DIR 明示 + README 追記

## 9. ロールバック / 安全策
- workflows/wan2_2_ti2v_5b を削除すれば元に戻せる
- UI変更は params 送信部分のみ戻せる

## 10. Plan closure（最後に必ず畳む）
- Done:
  - [ ] ...
- Blocked:
  - [ ] ...（1文理由 + 次に聞くべき質問）
- Cancelled:
  - [ ] ...（理由）
