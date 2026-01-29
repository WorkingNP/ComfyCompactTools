# Skills ディレクトリ

GPT Codex用のカスタムスキル（再利用可能なタスク定義）を配置します。

## スキルの構造

各スキルは独立したMarkdownファイルとして定義します：

```markdown
# {Skill Name}

## 目的
このスキルが何を実現するかを簡潔に説明

## 前提条件
- 必要な環境
- 依存関係

## 実行手順
1. ステップ1
2. ステップ2
3. ステップ3

## 検証方法
成功/失敗を判定する方法

## 例
具体的な使用例
```

## スキルの使用方法

### Codexセッション内で参照
```python
mcp__codex__codex({
    "prompt": "deploy-workflowスキルを実行して",
    "developer-instructions": ".codex/skills/deploy-workflow.md の手順に従ってください"
})
```

## スキル例

- `deploy-workflow.md` - ワークフローのデプロイ手順
- `run-tests.md` - テスト実行手順
- `generate-docs.md` - ドキュメント生成手順
