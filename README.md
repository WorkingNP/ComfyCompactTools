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

- 左の `Prompt` に入力して **Enter** → 即Queue
- 生成中でも Enter 連打でどんどん積める
- 右の Gallery に生成結果が勝手に増える
- サムネクリックで、画像とメタ情報（prompt/params）が見える
- Favorite ボタンでお気に入り切替（DB保存）

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

## この後の拡張（ロードマップ）

- i2i / inpaint（`/upload/image`, `/upload/mask` を使う）
- プロンプト資産管理（テンプレ／タグ／スニペット）
- Grokチャット欄 → JSON → 一括Queue
- Grok/VLMでの自動評価ループ（生成→評価→改善→再生成）
- Comfyのカスタムノード／ワークフローテンプレ取り込み

