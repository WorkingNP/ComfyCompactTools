# Grok-Comfy-Cockpit2 統合ルール（GPT Codex用）

このファイルは、GPT Codexセッション開始時に`base-instructions`として読み込むための統合ルールです。

---

## プロジェクト概要
このリポジトリは、ローカルComfyUIを叩いて画像生成する "コックピット" MVPです。

---

## 基本方針
- 既存機能を壊さない（後方互換を優先）
- テスト駆動で開発する
- ローカルのブラウザアプリUIに変更を加える際は：
  1. **Agent Browser（e2e-runnerエージェント）で自動テスト・スクリーンショット確認を優先**
  2. 必要に応じて手動でブラウザ確認
  3. 重要なUIフローは必ずE2Eテストを追加

---

## テスト方針
- UIテストはAgent Browser（Vercel Agent Browser）を優先的に使用
- e2e-runnerエージェントでテスト生成・実行・スクリーンショット取得を自動化
- 手動確認は自動テストで検出できない視覚的問題のみに限定

### テストレビュー時の必須チェック

#### 画像生成テスト
- [ ] ファイル存在チェックあるか
- [ ] ファイルサイズ > 0 チェックあるか
- [ ] 画像フォーマット検証あるか（Pillowで開けるか）
- [ ] 画像サイズ（width/height）検証あるか
- [ ] 真っ黒/真っ白の検出ロジックあるか

#### API連携テスト
- [ ] 接続成功時の正常系テストあるか
- [ ] 接続失敗時のエラーメッセージが明確か
- [ ] タイムアウト設定が適切か
- [ ] リトライロジックがあれば、その検証あるか

#### ファイル入出力テスト
- [ ] 一時ディレクトリ（tmp_path等）を使用しているか
- [ ] テスト後のクリーンアップは適切か
- [ ] パス区切り文字がOS非依存か（pathlib使用推奨）

---

## タスク固有ルール

### ComfyUI Workflow 作成・修正
**ComfyUI関連タスク（ワークフロー作成、テンプレート編集、manifest修正、パッチ処理実装など）を行う際は、必ず `.codex/rules/comfy-workflow-rules.md` を参照してから作業を開始してください。**

このルールには以下が含まれます：
- テンプレJSON + マニフェスト駆動の設計思想
- Workflow Registry の実装ガイド
- テスト駆動開発の必須ステップ
- 実装時の注意点と地雷回避策

`.codex/rules/comfy-workflow-rules.md` を参照せずにComfyUI関連の実装を進めることは禁止します。

### UI Testing with Agent Browser
UI変更時は、`.codex/rules/ui-testing-with-agent-browser.md` のガイドラインに従うこと。

---

## その他
- プロジェクト固有の依存追加は慎重に行い、理由を記録してください
- ComfyUIで使用するcheckpointは "C:\Users\souto\Desktop\ComfyUI_windows_portable\ComfyUI\models\checkpoints"

---

## 参照すべきルールファイル一覧

| ファイル名 | 用途 |
|-----------|------|
| `main.md` | プロジェクト基本ルール（CLAUDE.mdのコピー） |
| `comfy-workflow-rules.md` | ComfyUIワークフロー実装ルール |
| `testing-guidelines.md` | テストガイドライン詳細 |
| `ui-testing-with-agent-browser.md` | Agent Browserを使ったUIテスト手順 |
| `all-rules.md`（本ファイル） | 全ルールの統合版 |

---

## GPT Codex使用時の推奨設定

```toml
[profile.grok-comfy]
model = "gpt-5.2-codex"
sandbox = "workspace-write"
approval-policy = "on-failure"
base-instructions = ".codex/rules/all-rules.md"
```



---

## MCP Tool Priority
- When you need image generation, workflow listing, parameter discovery, or batch generation, use the `comfy_cockpit` MCP server tools first.

