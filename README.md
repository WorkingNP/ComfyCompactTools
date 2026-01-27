# Grok-Comfy Cockpit (MVP)

「ComfyUI を二度と触りたくない」ための、**固定3ペイン・キュー駆動・自動ギャラリー**のローカルWebアプリ（最小実装）です。

- **全体スクロールなし**（内部スクロールのみ）
- 生成待ちでも **PromptをバカバカQueue投入できる**
- 生成画像は **勝手にギャラリーに増える**
- 画像から **プロンプト／設定（レシピ）**を即確認

> これはフェーズ1の“縦に動く”土台です。ここから i2i / inpaint / Grokコックピット / 自動評価ループ / プロンプト資産管理 を積みます。

---

## 重要：GitHubに直接書ける？

この環境から **あなたのGitHubリポジトリへ直接 push / commit はできません**（権限・接続の都合）。

代わりに、こちらで **プロジェクト一式をフォルダとして生成**してあるので、あなたがローカルで `git init` → `git remote add` → `git push` で上げるのが最短です。

---

## 必要なもの

- ComfyUI がローカルで起動していること（既定: `http://127.0.0.1:8188`）
- Python 3.10+（ComfyUIが動いてるならだいたいOK）

---

## 起動手順

### 1) このリポジトリを配置

このフォルダ（`grok-comfy-cockpit/`）を好きな場所に置きます。

### 2) Python環境を用意

```bash
cd grok-comfy-cockpit
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) .env を作る

```bash
cp .env.example .env
```

- `COMFY_URL` が違う場合は変更
- もし checkpoint が見つからない／デフォルトが合わない場合は `COMFY_CHECKPOINT` を設定

### 4) サーバ起動

```bash
python -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8787
```

ブラウザで開く：

- `http://127.0.0.1:8787`

---

## 使い方（MVP）

### 基本的な使い方

1. **Workflow選択**
   - 左の「Workflow」セクションでワークフローを選択
   - Parametersセクションにmanifest駆動の動的フォームが生成される

2. **画像生成**
   - 左の `Prompt` に入力して **Enter** → 即Queue
   - 生成中でも Enter 連打でどんどん積める
   - 真ん中の Queue に生成状態が表示される
   - 右の Gallery に生成結果が勝手に増える

3. **画像の確認と再実行**
   - サムネクリックで、画像とメタ情報（prompt/params/workflow_id）が見える
   - Favorite ボタンでお気に入り切替（DB保存）
   - **Re-run ボタンで同じパラメータを復元して再生成**

4. **履歴機能**
   - 過去の生成ジョブはQueue欄に残る
   - 各ジョブの「Requeue」ボタンで再実行可能
   - WebSocket接続時に自動的に履歴が読み込まれる

---

## データ保存場所

- `./data/cockpit.sqlite3` : ジョブ・画像メタ・お気に入り状態
- `./data/assets/` : ダウンロードした画像（ComfyUIの出力をコピーして保持）

---

## トラブルシュート

### チェックポイント一覧が空

- ComfyUIが起動しているか確認
- ComfyUIの `models/checkpoints` にモデルが入っているか確認
- それでもだめなら `.env` で `COMFY_CHECKPOINT` を直指定してください

### 生成は走るがGalleryに出ない

- ComfyUIが `SaveImage` を含むワークフローになっている必要があります（本MVPは固定ワークフローを投げています）
- ComfyUIの出力フォルダ設定や権限が変だと /view が失敗することがあります

---

## UI Features (Phase 5)

### Workflow選択とManifest駆動フォーム

- UIは `/api/workflows` から利用可能なワークフローを取得
- Workflow選択時に `/api/workflows/{id}` から params_schema を取得
- manifest の `params` 定義に基づいて動的にフォームを生成
  - `type: string` → text input / textarea
  - `type: integer` → number input (with min/max/step)
  - `type: float` → number input
  - `type: boolean` → checkbox
  - `choices` → select dropdown
- 新しいワークフローを追加すると、自動的にUIに表示される（データ駆動）

### Re-run機能

- ギャラリーの画像をクリック→モーダル表示
- 「Re-run」ボタンで元のworkflow_idとparamsをフォームに復元
- プロンプトを編集して再生成も可能

### Health Status

- 起動時に `/api/health` をチェック
- ComfyUIの接続状態を視覚的に表示
  - 緑: 接続成功
  - 赤: 接続失敗（unreachable / error）

### ディレクトリトラバーサル対策

- `/assets/{filename}` は FastAPI の StaticFiles で配信
- ファイル名に `..` が含まれていても安全に処理される

## Workflow Registry

The cockpit supports multiple workflows through a template + manifest architecture.

### Available Workflows

| Workflow ID | Description | Default |
|-------------|-------------|---------|
| `flux2_klein_distilled` | Flux 2 Klein 4B distilled (fast, 4 steps) | **Yes** |
| `sd15_txt2img` | Classic Stable Diffusion 1.5 text-to-image | No |
| `sdxl_txt2img` | Stable Diffusion XL 1.0 text-to-image with external VAE | No |

### SDXL Workflow

The SDXL (Stable Diffusion XL) workflow supports:
- **Checkpoint selection** from local models directory
- **External VAE selection** (separate VAE loader for better quality)
- **SDXL-optimized defaults** (1024x1024, 30 steps)
- Full control over sampler, scheduler, CFG, seed, and batch size

#### Configuration

Configure model directories in `config.json`:

```json
{
  "checkpoints_dir": "C:\\Users\\souto\\Desktop\\ComfyUI_windows_portable\\ComfyUI\\models\\checkpoints",
  "vae_dir": "C:\\Users\\souto\\Desktop\\ComfyUI_windows_portable\\ComfyUI\\models\\vae"
}
```

Or via environment variables:

```bash
# Windows (PowerShell)
$env:COMFY_CHECKPOINTS_DIR="C:\path\to\checkpoints"
$env:COMFY_VAE_DIR="C:\path\to\vae"

# Linux/Mac
export COMFY_CHECKPOINTS_DIR="/path/to/checkpoints"
export COMFY_VAE_DIR="/path/to/vae"
```

The workflow dynamically populates dropdown choices based on available models in these directories.

### Using a Workflow

**Default workflow (flux2_klein_distilled):**

```bash
# workflow_id is optional - klein is the default
curl -X POST http://127.0.0.1:8787/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat"}'
```

**Specifying a different workflow:**

```bash
curl -X POST http://127.0.0.1:8787/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat", "workflow_id": "sd15_txt2img"}'
```

### API Endpoints

**Workflows**
- `GET /api/workflows` - List available workflows
- `GET /api/workflows/{id}` - Get workflow details (params, presets)
- `POST /api/workflows/reload` - Reload workflows after adding new ones

**Jobs (Generation)**
- `POST /api/jobs` - Create a new generation job
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{id}` - Get job status, progress, and metadata

**Assets**
- `GET /api/assets` - List all generated assets
- `GET /api/assets/{id}` - Get asset details
- `GET /assets/{filename}` - Download asset file

**Health**
- `GET /api/health` - Check server and ComfyUI connection status

#### Example: Create and Monitor a Job

```bash
# 1. Create a job
curl -X POST http://127.0.0.1:8787/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a beautiful sunset"}' | jq

# Response: {"id": "abc123...", "status": "queued", ...}

# 2. Check job status
curl http://127.0.0.1:8787/api/jobs/abc123... | jq

# 3. Check health (includes ComfyUI connection status)
curl http://127.0.0.1:8787/api/health | jq
# Response: {"ok": true, "comfy_url": "...", "error_code": null, ...}
```

### Adding a New Workflow

1. Create a directory: `workflows/<your_workflow_id>/`
2. Export your ComfyUI workflow as API format: **File > Save (API Format)**
3. Save it as `workflows/<your_workflow_id>/template_api.json`
4. Create `workflows/<your_workflow_id>/manifest.json`:

```json
{
  "id": "your_workflow_id",
  "name": "Your Workflow Name",
  "description": "What this workflow does",
  "version": "1.0.0",
  "template_file": "template_api.json",
  "params": {
    "prompt": {
      "type": "string",
      "required": true,
      "patch": {
        "node_id": "6",
        "field": "inputs.text"
      }
    },
    "seed": {
      "type": "integer",
      "default": -1,
      "patch": {
        "node_id": "25",
        "field": "inputs.noise_seed"
      }
    }
  }
}
```

5. Reload workflows: `POST /api/workflows/reload`

**Dynamic Model Choices:** If your workflow has `checkpoint` or `vae` parameters, the system will automatically populate their dropdown choices by scanning the configured model directories (`checkpoints_dir` and `vae_dir` in settings).

See `docs/03_manifest_spec.md` for full manifest documentation and examples (`flux2_klein_distilled`, `sd15_txt2img`, `sdxl_txt2img`).

---

## Testing

```bash
# Unit + Integration tests (no ComfyUI required)
pytest server/tests/ -v -m "not e2e"

# E2E tests (requires ComfyUI + server running)
pytest server/tests/ -v -m "e2e"

# All tests
pytest server/tests/ -v
```

**Note:** E2E tests are automatically skipped if ComfyUI or the server is not running.

---

## MCP Server (Phase 6)

Cockpit now includes an MCP (Model Context Protocol) server that allows LLMs (like Codex, Claude, or local LLMs) to generate images via tool calls.

### Starting the MCP Server

```bash
# Default: connects to http://127.0.0.1:8787
python -m server

# Custom Cockpit URL:
COCKPIT_BASE_URL=http://localhost:8787 python -m server
```

### Configuring in Claude Desktop (or Codex)

Add to your `claude_desktop_config.json` (or equivalent):

```json
{
  "mcpServers": {
    "cockpit-image-generator": {
      "command": "python",
      "args": ["-m", "server"],
      "cwd": "C:/path/to/grok-comfy-cockpit2",
      "env": {
        "COCKPIT_BASE_URL": "http://127.0.0.1:8787"
      }
    }
  }
}
```

### Available MCP Tools

1. **workflows_list** - List all available workflows
2. **workflow_get** - Get workflow details and parameters
3. **images_generate** - Generate images (with polling until complete)
   - Supports `count` parameter to generate multiple images with same params
   - Returns image URLs ready to display
4. **images_generate_many** - Batch generate with multiple prompts
   - Perfect for "generate 10 variations" use cases

### Example Usage (from LLM)

```
User: "Generate 3 images of cats with different styles"

LLM calls:
  images_generate_many(
    prompts=["a realistic cat", "a cartoon cat", "a cyberpunk cat"],
    workflow_id="flux2_klein_distilled",
    base_params={"width": 832, "height": 1024}
  )

Returns:
  {
    "results": [
      {"prompt": "a realistic cat", "outputs": ["http://...asset1.png"]},
      {"prompt": "a cartoon cat", "outputs": ["http://...asset2.png"]},
      {"prompt": "a cyberpunk cat", "outputs": ["http://...asset3.png"]}
    ],
    "ui_url": "http://127.0.0.1:8787/"
  }
```

---

## この後の拡張（ロードマップ）

- i2i / inpaint（`/upload/image`, `/upload/mask` を使う）
- プロンプト資産管理（テンプレ／タグ／スニペット）
- Grokチャット欄 → JSON → 一括Queue
- Grok/VLMでの自動評価ループ（生成→評価→改善→再生成）
- ControlNet / XYZ Plot workflows
- Dynamic UI form generation from manifests

