# Rules ディレクトリ

GPT Codex用のプロジェクトルールを配置します。

## ファイル命名規則

- `main.md` - メインのプロジェクトルール（最初に読み込まれる）
- `{domain}-rules.md` - ドメイン固有のルール（例：`comfy-workflow-rules.md`）
- `{task}-guidelines.md` - タスク固有のガイドライン

## ルールの読み込み方法

### 方法1: base-instructions パラメータ
```python
with open(".codex/rules/main.md") as f:
    rules = f.read()

mcp__codex__codex({
    "prompt": "画像生成ワークフローを実装して",
    "base-instructions": rules
})
```

### 方法2: developer-instructions パラメータ
```python
mcp__codex__codex({
    "prompt": "画像生成ワークフローを実装して",
    "developer-instructions": "必ず .codex/rules/comfy-workflow-rules.md を読んでから作業すること"
})
```

## Claude Code との使い分け

- **Claude Code (`.claude/rules/`)**: インタラクティブな開発、プランニング、レビュー
- **GPT Codex (`.codex/rules/`)**: 自動化タスク、バッチ処理、CI/CD統合

共通のルールは両方にシンボリックリンクまたはコピーして配置することを検討してください。
