# プロジェクト固有のガイドライン

## テスト作成・レビュー時

1. `.claude/testing-guidelines.md` を読む
2. チェックリストを既存テストに適用
3. 不足があれば指摘または修正提案
4. 判断に迷う場合はユーザーに確認

## プロジェクト構成

- `comfy_flux2_api_pack/` - ComfyUI Flux.2 API連携スクリプト
  - `comfy_flux2_generate.py` - Flux.2 dev用
  - `comfy_flux2_klein_generate.py` - Flux.2 klein用
  - `flux2_*_prompt_template.json` - APIワークフローテンプレート
  - `tests/` - E2Eテスト
