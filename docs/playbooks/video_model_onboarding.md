# Video Model Onboarding Playbook (Wan2.2 TI2V 実装で得た知見)

目的: 次の動画生成系モデル導入で「仕様・実装・UI」を切り分け、最短で安定動作まで持っていく。

---

## 1) TL;DR (最短ルート)
1. 公式テンプレ/推奨値を確認
2. manifest + template を作成（推奨値を default に設定）
3. APIテストで params/patch を固定
4. サーバー再起動 or /api/workflows/reload（指示待ちせず自動で実施）
5. UIは最後（Phase2）に追加
6. 出力確認は手動で ComfyUI output を見る

---

## 2) 公式テンプレ確認ポイント
- 推奨解像度 (width/height)
- 推奨 length / fps
- 推奨 steps / cfg
- sampler / scheduler
- 必要な入力 (start_image の有無)

※ 公式テンプレ JSON をそのまま保存して参照するのが安全。

---

## 3) ワークフロー導入手順 (API優先)
1) workflows/<id>/manifest.json を作成
- required / default / type / patch の定義
- 推奨値は default に入れる
- prompt/negative_prompt の初期値もここに入れる

2) workflows/<id>/template_api.json を作成
- 公式テンプレの node_id/field に合わせる
- default が template と食い違わないよう揃える

3) APIテスト追加
- /api/workflows に id が出る
- /api/workflows/{id} に params が出る
- 重要デフォルト (width/height/length/fps/steps/cfg) をアサート
- start_image など image param の patch をアサート

---

## 4) デフォルト値の決め方
- 基本: 公式推奨値 = default
- 例外: 低コストで試す必要がある場合は preview preset を別に用意

推奨: default は公式、preview は presets に追加

---

## 5) サーバー再起動/反映の注意
### よくある症状
- UIに新ワークフローが出ない
- /api/uploads/image が 405 になる

### 反映手順
- まず /api/workflows/reload を叩く
- それでもダメならサーバー再起動（指示待ち不要）
- /openapi.json で新エンドポイントが出ているか確認

判定例:
- /api/uploads/image が openapi に無い = 古いプロセスが残っている

---

## 6) UIは別フェーズ推奨
理由:
- API/manifest が固まってから UI を触ると原因切り分けが容易
- UI の不具合と backend の不具合が混ざらない
- テスト設計がシンプルになる

フェーズ分割:
- Phase1: manifest + patcher + API tests
- Phase2: UI (HTML/JS)
- Phase3: E2E

---

## 7) E2E 方針 (動画生成)
- 自動: UI操作まで（workflow 選択、入力、送信）
- 手動: 生成結果の品質確認（ComfyUI output で確認）

理由: 動画品質は自動判定が難しいため

---

## 8) 典型的な落とし穴
- start_image が2分割/比較画像 → 出力がそのまま崩れる
- 画像解像度が推奨と不一致 → 崩れやすい
- 古いサーバープロセスが残る → 405 や新APIが見えない

---

## 9) 実装チェックリスト (次回用)
- [ ] 公式テンプレ JSON を入手
- [ ] manifest defaults を公式推奨値に揃える
- [ ] /api/workflows/{id} の params が期待どおり
- [ ] /api/uploads/image の動作確認
- [ ] UI 反映 (reload or restart)
- [ ] E2E (UI操作 + スクショ)
- [ ] 出力は手動確認 (ComfyUI output)

---

## 10) 参考
- 公式テンプレ: Comfy-Org workflow_templates
- ComfyUI output の手動確認を前提にする
