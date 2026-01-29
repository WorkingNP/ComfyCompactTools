# Prompts ディレクトリ

再利用可能なプロンプトテンプレートを配置します。

## プロンプトの種類

### 1. タスクプロンプト
特定のタスクを実行するための指示テンプレート

```markdown
# {Task Name} Prompt

## コンテキスト変数
- `{workflow_name}` - ワークフロー名
- `{target_file}` - 対象ファイル

## プロンプト本文
{{workflow_name}}ワークフローの{{target_file}}を実装してください。
以下の要件を満たすこと：
1. ...
2. ...
```

### 2. レビュープロンプト
コード/ドキュメントレビュー用のテンプレート

### 3. 分析プロンプト
既存コードを分析するためのテンプレート

## プロンプトの使用方法

### Python経由で変数を埋め込んで使用
```python
with open(".codex/prompts/implement-workflow.md") as f:
    template = f.read()

prompt = template.format(
    workflow_name="flux-img2img",
    target_file="server/workflows/flux_img2img.py"
)

mcp__codex__codex({"prompt": prompt})
```

## プロンプト例

- `implement-workflow.md` - ワークフロー実装用
- `review-code.md` - コードレビュー用
- `write-tests.md` - テスト作成用
