# Issue分割ベストプラクティス

## 概要

このドキュメントは、コードレビューやプランニングから得られた問題をどのようにIssueに分割すべきかのガイドラインです。

## 基本原則

### 1. 優先度による分類

**CRITICAL / HIGH（緊急）**
- システムの安定性やセキュリティに影響
- ユーザー体験を著しく損なう
- 即座に対応すべき
- 例：メモリリーク、認証バイパス、データ損失

**MEDIUM（推奨）**
- 機能改善やパフォーマンス向上
- 次のリリースサイクルで対応
- 例：バリデーション強化、エラーメッセージ改善

**LOW（将来的）**
- Nice-to-have機能
- 技術的負債の返済
- リファクタリング
- 例：コードの可読性向上、テストカバレッジ追加

### 2. スコープの明確化

**1つのIssueは1つの責務**
- 単一の問題や機能に焦点を当てる
- 複数の無関係な変更を1つのIssueにまとめない
- ただし、密接に関連する変更は1つにまとめる

**適切なサイズ**
- 小さすぎる：1行の変更 → 他の関連修正とまとめる
- 大きすぎる：複数ファイルで異なる責務 → 分割する
- 目安：1-3日で完了できる規模

### 3. 依存関係の考慮

**直列依存**
```
Issue A (必須) → Issue B (推奨) → Issue C (将来)
```
- Issue Bは Issue Aの完了後のみ実装可能

**並列可能**
```
Issue A (バリデーション)
Issue B (非同期対応)  ← 独立して実装可能
Issue C (テスト追加)
```

## Issue分割の判断フロー

```
問題発見
  ↓
優先度評価 (CRITICAL/HIGH/MEDIUM/LOW)
  ↓
依存関係確認 (他のIssueへの依存有無)
  ↓
スコープ明確化 (単一責務か？)
  ↓
【分割判断】
  ├─ 密接に関連している → 1つのIssueにまとめる
  ├─ 独立して実装可能 → 別々のIssueに分割
  └─ 依存関係がある → 順序付きでIssue作成
```

## PR戦略

### 1つのPRにまとめる場合

**メリット：**
- 全体の整合性を保ちやすい
- レビュアーが文脈を理解しやすい
- マージ後の動作確認が1回で済む

**適用例：**
- 同じモジュールの関連修正
- テストと実装のセット
- リファクタリングとバグ修正が密接

**コミット分割：**
```bash
git commit -m "test: add async test structure"
git commit -m "refactor: convert to async/await"
git commit -m "feat: add partial failure handling"
git commit -m "feat: add validation"
```

### 複数のPRに分ける場合

**メリット：**
- 独立してレビュー・マージ可能
- 問題が発生した際のロールバックが容易
- 並列で作業可能

**適用例：**
- 優先度が大きく異なる（CRITICAL vs LOW）
- 異なるモジュール・機能
- 大規模な変更（100ファイル以上）

**PR順序：**
```
PR #1: CRITICAL修正 → マージ → デプロイ
PR #2: MEDIUM改善 → レビュー待ち
PR #3: LOW改善 → 後日対応
```

## コードレビューからのIssue抽出

### Codexレビュー結果の例（2026-01-29実施）

**入力：** コミット前の差分をCodexに渡す

**出力：** 優先度別の問題リスト
```
HIGH:
- 非同期ブロッキング修正
- 部分失敗ハンドリング

MEDIUM:
- DoS対策（リソース制限）
- プロンプト検証強化
- seed型チェック
```

### Issue作成の実例

#### Issue #1: MCP非同期ブロッキング修正（CRITICAL）
**タイトル:** Fix async blocking in MCP tools (time.sleep → asyncio.sleep)

**概要:**
- `time.sleep()` がMCPサーバーをブロック
- async/await対応でイベントループフリーズを解消
- 全MCPツールに影響

**スコープ:**
- server/mcp_tools.py
- server/__main__.py
- server/tests/test_mcp_tools.py

**受け入れ基準:**
- [ ] `images_generate()` が `async def`
- [ ] `images_generate_many()` が `async def`
- [ ] すべてのテストがpytest-asyncioで実行可能
- [ ] 既存テストがすべてパス

**実装時間:** 2-4時間

#### Issue #2: 部分失敗ハンドリングと入力検証（HIGH）
**タイトル:** Handle partial failures and validate inputs in batch operations

**概要:**
- バッチ処理の部分失敗時も成功分を返す
- 空プロンプトリストで空結果を返す
- リソース制限追加

**依存:** Issue #1完了後（async対応が前提）

**スコープ:**
- server/mcp_tools.py
- server/tests/test_mcp_tools.py

**受け入れ基準:**
- [ ] ジョブ作成で一部失敗しても成功分を返す
- [ ] 空プロンプトで `{"results": [], "ui_url": "..."}` を返す
- [ ] count最大100、prompts最大50の制限
- [ ] テストで部分失敗と検証をカバー

**実装時間:** 3-5時間

## 今回の実装例（2026-01-29）

### 採用戦略：1つのPRにまとめる

**理由：**
- Issue #1とIssue #2は密接に関連（部分失敗処理はasync前提）
- 同じファイル群を変更（mcp_tools.py, __main__.py）
- テスト駆動で一貫性を保てる

**コミット履歴：**
```
1. test: add pytest-asyncio dependency
2. refactor: convert MCP tools to async/await
3. feat: handle partial failures in batch jobs
4. feat: add input validation and resource limits
5. docs: add issue splitting best practices
```

**結果：**
- 31テスト全パス
- カバレッジ: 80%達成
- レビュー・マージが一度で完了

## 判断が難しいケース

### ケース1: バグ修正 + リファクタリング

**問題：** バグ修正のためにリファクタリングが必要

**判断：**
- バグが緊急（CRITICAL） → リファクタリングも含めて1つのPR
- バグが軽微（MEDIUM） → バグ修正PRとリファクタリングPRを分ける

### ケース2: 新機能 + 既存機能改善

**問題：** 新機能追加時に既存機能の問題を発見

**判断：**
- 既存機能の問題が新機能に影響 → 1つのPR
- 独立している → 別々のIssue/PR

### ケース3: ドキュメント更新

**問題：** コード変更に伴うドキュメント更新

**判断：**
- APIやインターフェース変更 → コードと同じPR
- ベストプラクティス追加 → 別PR（後からでも可）

## チェックリスト

### Issue作成時
- [ ] タイトルは明確か（動詞で始まる）
- [ ] 優先度を設定したか
- [ ] スコープを明確にしたか
- [ ] 受け入れ基準を記載したか
- [ ] 依存関係を確認したか
- [ ] 実装時間を見積もったか

### PR作成時
- [ ] 関連Issueをリンクしたか
- [ ] コミットを論理的に分割したか
- [ ] テストがすべてパスしているか
- [ ] レビュアーに文脈を説明したか
- [ ] 変更の影響範囲を確認したか

## まとめ

**原則：**
1. 優先度で分類（CRITICAL/HIGH/MEDIUM/LOW）
2. 単一責務を保つ
3. 依存関係を明確にする
4. 適切なサイズに保つ（1-3日）

**判断基準：**
- 密接に関連 → 1つのPR
- 独立可能 → 複数のPR
- 緊急度が高い → 優先的にマージ

**TDDとの連携：**
- テスト駆動で実装することで、スコープの明確化が容易
- RED → GREEN → REFACTORのサイクルがコミット分割の基準になる

## 参考資料

- 計画ファイル：`.claude/plans/abundant-pondering-beacon.md`
- TDDワークフロー：`.claude/rules/tdd-workflow.md`
- コードレビュー：`.claude/rules/testing-guidelines.md`
