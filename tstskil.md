あなたはComfyCompactTools（WorkingNP/ComfyCompactTools またはそのfork）の開発者として振る舞ってください。
目的は「新しいワークフローを “データ駆動” で追加し、UI/API/MCP経由で安定して使える状態（DoD）まで持っていく」ことです。

# 前提（重要）
- サーバコード改修は原則しない。ワークフロー追加は workflows/<workflow_id>/ の追加で完結させる。
- ワークフローは ComfyUI の「API形式（File > Save (API Format)）」のJSON（template_api.json）を使う前提。
- Gallery表示のため SaveImage を含むこと（MVP前提）。

# あなたがやるタスク
## 0) ユーザー入力（あなたが使う情報）
ユーザーからの指定が無い場合、例を参考に命名すること。
- workflow_id: <<workflow_id>>   （例: wan22_t2v_5b / qwen_image_edit / sdxl_txt2img など）
- name: <<name>>
- description: <<description>>
- version: <<version>>（例: "1.0.0"）
- template_api.json: 
  - C:\Users\souto\Desktop\grok-comfy-cockpit2\workflows\flux2_klein_distilled\template_api.json
  - 無い場合は、私がこのチャットで貼るので、それをそのまま workflows/<id>/template_api.json に保存して使う
- 追加したいパラメータ（候補。必要なものだけ採用してよい）:
  - prompt（必須）
  - negative_prompt（任意）
  - seed（必須。-1=ランダム など運用ルールがあればそれに合わせる。デフォルトは-1、もしくはランダムシードを意味する数値）
  - steps / cfg (必須)
  - width / height（必須。テンプレ側で変更可能なら）
  - batch_size / num_images（仕組み問題がなければ必須）
  - その他このワークフロー特有のパラメータ（例: frames, fps, denoise, strength, guidance 等）

## 1) 実装（ファイル作成）
workflows/<<workflow_id>>/ を作り、次の2ファイルを作成してください。

### A) workflows/<<workflow_id>>/template_api.json
- テンプレはComfyUIのAPI形式JSON。
- 変更が必要なら「manifestのpatchが差し込めるようにする」範囲で最小限にする。
- SaveImage が含まれること。

### B) workflows/<<workflow_id>>/manifest.json
- 既存のREADME/既存workflowのmanifest形式に必ず合わせる（キー名・構造を揃える）。
- 最低限 id/name/description/version/template_file/params を持つ。
- paramsはUIフォーム生成に使われるので、型・デフォルト・min/max/step/choices 等を適切に付ける。
- 各paramには patch を必ず付ける：
  - patch.node_id: template_api.json 内の該当ノードID
  - patch.field: 例 "inputs.text" / "inputs.noise_seed" のような dot path
- node_id と field は推測ではなく、template_api.json を実際に読んで確定させること。
  - prompt/negative_prompt はCLIPTextEncode等のノード inputs.text を狙うことが多い
  - seed/steps/cfg はKSampler等の inputs.noise_seed / inputs.steps / inputs.cfg を狙うことが多い
  - width/height はEmptyLatentImage等の inputs.width / inputs.height を狙うことが多い
  （ただしテンプレによるので必ずJSONから確定させる）

## 2) 検証（DoDを満たす）
あなたは最終出力として、下のDoDチェックリストを「このワークフローで満たしたか」を◯/△/×で埋め、必要な手順コマンド例も書いてください。

--- DoD（完成条件）---

### DoD-1 Bronze（Cockpit上で動く）
[ ] workflows/<id>/template_api.json と manifest.json が存在
[ ] manifestの id とフォルダ名が一致
[ ] /api/workflows/reload 後に一覧に出る
[ ] UIでフォームが表示される（manifest.params駆動）
[ ] Prompt→Queueでジョブ投入できる
[ ] 生成結果がGalleryに出る（SaveImage前提）
[ ] APIで最低限これが通る：
    - POST /api/jobs で job作成（workflow_id指定）
    - GET /api/jobs/<job_id> で状態取得

### DoD-2 Silver（MCP経由で動く）
[ ] workflows_list に workflow_id が出る
[ ] workflow_get でparams schemaが取れる
[ ] images_generate で workflow_id 指定して生成→URLが返る
[ ] images_generate_many が複数プロンプトで動く（可能なら）

### DoD-3 Gold（運用耐性）
[ ] not e2e のpytestが壊れない（既存テスト維持）
[ ] e2eで「成果物URLが返る」確認ができる手順/テストがある（追加できるなら追加）
[ ] description と推奨デフォ値が妥当
[ ] 失敗時のメッセージ/制約が運用に耐える（min/max/choicesで事故防止）

--- DoDここまで ---

# 3) 出力形式（必須）
あなたの最終回答には必ず次を含めてください：
1) 変更/追加したファイル一覧（相対パス）
2) manifest.json の全文（コピペ可能）
3) template_api.json が既存なら「使用したパス」、新規なら「（私が貼ったものを保存してOK）」の指示
4) DoDチェック結果（Bronze/Silver/Gold）
5) 動作確認の手順（curl例 or 手順箇条書き。/api/workflows/reload、/api/jobs、MCPツール呼び出し例）

# 制約（守って）
- 不要な改修を広げない（ワークフロー追加で完結）。
- node_id/patch.field はテンプレJSONから確定する。
- “それっぽい”推測で済ませない。テンプレを読めないなら、読むために必要な情報（私に貼ってもらう箇所）を具体的に要求してから進める。
