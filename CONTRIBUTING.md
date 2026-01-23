# Contributing Guide - 並列実装の境界線

このドキュメントは、複数のLLM/チャットで並列実装しても衝突しにくいように「触っていい領域」を明文化しています。

---

## 担当別の境界線

### 1. ワークフロー追加担当

**触っていいファイル:**
- `workflows/<new_workflow_id>/` - 新しいワークフローディレクトリ全体
- `workflows/<new_workflow_id>/manifest.json`
- `workflows/<new_workflow_id>/template_api.json`
- `server/tests/test_e2e_<new_workflow_id>.py` - 新しいワークフロー専用のE2Eテスト
- `tests/fixtures/<new_workflow_id>/` - 新しいワークフロー用のfixture

**原則触らない:**
- `server/workflow_registry.py` - 既存のregistryロジック
- `server/workflow_patcher.py` - パッチ適用ロジック
- 他のワークフローの `manifest.json` や `template_api.json`

**成功条件:**
1. `manifest.json` + `template_api.json` が正しく配置されている
2. `GET /api/workflows` でリストに表示される
3. オフラインテストまたはfixture検証が通る
4. （任意）E2Eテストが通る

---

### 2. コア担当（Registry / Patcher）

**触っていいファイル:**
- `server/workflow_registry.py`
- `server/workflow_patcher.py`
- `server/image_quality.py`
- `server/tests/test_workflow_registry.py`
- `server/tests/test_patcher.py`
- `server/tests/test_image_quality.py`
- `docs/03_manifest_spec.md` - マニフェスト仕様

**注意:**
- 変更は小さく刻む（1PR/1機能）
- 既存ワークフローの動作を壊さない
- テストを先に書く（テストファースト）

**成功条件:**
1. 既存のユニットテストが全て通る
2. 新機能のテストが追加されている
3. 既存ワークフローが引き続き動作する

---

### 3. UI担当

**触っていいファイル:**
- `web/` 配下のフロントエンドファイル
- `server/main.py` の UI関連エンドポイント（`/api/assets`, `/api/jobs` など）

**原則触らない:**
- `workflows/` 配下のファイル
- `server/workflow_registry.py`
- `server/workflow_patcher.py`

**境界線:**
- manifestを **読む** だけに徹する
- ワークフロー追加担当と衝突しないように、動的フォーム生成は manifest のスキーマに依存

---

### 4. 品質担当

**触っていいファイル:**
- `server/image_quality.py` - 画像検証ロジック
- `server/tests/test_image_quality.py`
- 各ワークフローの `manifest.json` 内の `quality_checks` セクション

**責務:**
- 黒/白/単色画像の検出ロジックを一箇所に集約
- 閾値のチューニング
- ワークフローごとの閾値カスタマイズ（`manifest.json` の `quality_checks.skip_checks` など）

---

## ファイル構造と所有権

```
grok-comfy-cockpit2/
├── workflows/                    # ワークフロー追加担当
│   ├── flux2_klein_distilled/   # デフォルトワークフロー
│   │   ├── manifest.json
│   │   └── template_api.json
│   └── sd15_txt2img/
│       ├── manifest.json
│       └── template_api.json
├── server/
│   ├── workflow_registry.py     # コア担当
│   ├── workflow_patcher.py      # コア担当
│   ├── image_quality.py         # 品質担当
│   ├── main.py                  # 共有（慎重に）
│   └── tests/
│       ├── test_workflow_registry.py  # コア担当
│       ├── test_patcher.py            # コア担当
│       ├── test_image_quality.py      # 品質担当
│       └── test_e2e_workflows.py      # 共有
├── scripts/
│   └── capture_fixtures.py      # 品質担当
├── tests/fixtures/              # ワークフロー追加担当
│   └── <workflow_id>/
└── web/                         # UI担当
```

---

## テスト戦略

### オフラインテスト（ComfyUI不要）
```bash
pytest server/tests/ -v -m "not e2e"
```

### E2Eテスト（ComfyUI + サーバー必要）
```bash
pytest server/tests/ -v -m "e2e"
```

### 特定ワークフローのテストのみ
```bash
pytest server/tests/test_e2e_workflows.py -v -k "klein"
```

---

## Fixture録画手順

新しいワークフローを追加したら、オフラインテスト用のfixtureを録画：

```bash
python scripts/capture_fixtures.py \
  --workflow-id <your_workflow_id> \
  --prompt "a test image" \
  --output tests/fixtures/<your_workflow_id>/
```

詳細は `scripts/capture_fixtures.py --help` を参照。

---

## 衝突を避けるためのルール

1. **PRは小さく** - 1つのPRで1つの機能/修正
2. **テストファースト** - 実装前にテストを書く
3. **境界を越えない** - 自分の担当外のファイルは触らない
4. **コミュニケーション** - 境界を越える必要がある場合は事前に相談
5. **デフォルトワークフロー** - `flux2_klein_distilled` がデフォルト。変更する場合は全員に影響するので慎重に
