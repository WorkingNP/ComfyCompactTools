# プロジェクト共通ルール

## プロジェクト概要
このリポジトリは、ローカルComfyUIを叩いて画像生成する "コックピット" MVPです。

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

---

## タスク固有ルール

### ComfyUI Workflow 作成・修正
**ComfyUI関連タスク（ワークフロー作成、テンプレート編集、manifest修正、パッチ処理実装など）を行う際は、必ず `docs/comfy_workflow_rules.md` を Read ツールで読み込んでから作業を開始してください。**

このルールには以下が含まれます：
- テンプレJSON + マニフェスト駆動の設計思想
- Workflow Registry の実装ガイド
- テスト駆動開発の必須ステップ
- 実装時の注意点と地雷回避策

`docs/comfy_workflow_rules.md` を参照せずにComfyUI関連の実装を進めることは禁止します。

---

## その他
- planner、tdd-guide などの既存エージェントは通常通り使用可能です
- プロジェクト固有の依存追加は慎重に行い、理由を記録してください
- ComfyUIで使用するcheckpointは "C:\Users\souto\Desktop\ComfyUI_windows_portable\ComfyUI\models\checkpoints"


---

## MCP Tool Priority
- When you need image generation, workflow listing, parameter discovery, or batch generation, use the `comfy_cockpit` MCP server tools first.

