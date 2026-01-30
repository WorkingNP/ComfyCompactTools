あなたは既存リポジトリに機能を“最小差分で”追加する統合エンジニアです。
目的は「ComfyUIの LTX-Video 0.9.5 の Image-to-Video（開始画像1枚）ワークフローを、既存プロジェクトのワークフロー群に追加し、CLI/API/バッチから再現性ある形で実行できるようにする」ことです。

# 前提（重要）
- リポジトリ内には既に「ワークフローの登録/実行/ログ/成果物出力」の仕組みがあるはず。まずそれを尊重し、同じ流儀で LTX I2V を追加する。
- ComfyUI はローカル or LAN上で起動しており、HTTP APIで叩ける前提（/prompt, /history, /view, /upload/image を使用）。
- 公式 LTX I2V workflow JSON（ComfyUI Examplesのもの）をテンプレとして使う。
- “勝手に大改造”は禁止。既存の抽象化・ディレクトリ命名・設定方式に合わせる。

# あなた（LLM）が最初にやること（分析）
1) リポジトリを走査し、以下を特定して要約せよ：
   - ワークフロー（またはパイプライン）定義の置き場（例: workflows/, pipelines/, assets/workflows/, etc）
   - ワークフローの登録方式（ID、メタデータ、カテゴリ分け、UI表示名など）
   - 実行方式（ローカル実行 / サーバ実行 / ジョブキュー / 非同期処理の有無）
   - 入出力規約（inputs/, outputs/、成果物の命名、メタデータjson、ログ）
   - 既にComfyUI連携があるか（あるならそのクライアントを再利用）

2) その上で「LTX I2V を同じ流儀で追加する最小変更点」を設計せよ。

# 追加したいワークフロー（LTX I2V simple）の仕様
- テンプレ: ltxv_image_to_video_simple.0.9.5.json（ComfyUI Examples: LTXV）
- テンプレ内の主要ノード（公式JSON準拠：このIDを前提にパッチする）
  - id=44  type=CheckpointLoaderSimple
      widgets_values[0] = "ltx-video-2b-v0.9.5.safetensors"（チェックポイント名）
  - id=38  type=CLIPLoader
      widgets_values[0] = "t5xxl_fp16.safetensors"（または fp8）
      widgets_values[1] = "ltxv"（ここは維持）
  - id=78  type=LoadImage
      widgets_values[0] = 入力画像ファイル名（ComfyUIの input フォルダに存在する前提）
  - id=6   type=CLIPTextEncode  title="CLIP Text Encode (Positive Prompt)"
      widgets_values[0] = positive prompt（文字列）
  - id=7   type=CLIPTextEncode  title="CLIP Text Encode (Negative Prompt)"
      widgets_values[0] = negative prompt（文字列）
  - id=95  type=LTXVImgToVideo
      widgets_values = [width, height, frames, 1]
      ※4つ目はテンプレ通り 1 を基本維持（意味が不明な場合は触らない）
  - id=71  type=LTXVScheduler
      widgets_values[0] = steps（例: 30）※他の値はテンプレ維持でOK
  - id=72  type=SamplerCustom
      widgets_values = [true, seed, "randomize"/"fixed", cfg]
      例: [true, 109284..., "randomize", 3]
  - id=86  type=SaveWEBM
      widgets_values = [output_prefix, codec, fps, quality_or_crf]
      例: ["ComfyUI","vp9",24,12] を
          ["ltx_i2v","vp9",fps,12] に変更可能

- 生成に必要なモデル配置（ドキュメントに明記する）
  - ComfyUI/models/checkpoints/ltx-video-2b-v0.9.5.safetensors
  - ComfyUI/models/text_encoders/t5xxl_fp16.safetensors（または fp8）
  - ※モデルを外部に置く場合は extra_model_paths.yaml を使う（既存運用があるならそれに合わせる）

# 実装タスク（あなたが出す成果物）
A) ワークフロー資産の追加
- 公式テンプレJSONをリポジトリに取り込む（既存の置き場所に合わせる）
  例: assets/comfyui/workflows/ltxv_i2v_simple_0.9.5.json
- “テンプレは触らず”、実行時にパッチする方式を優先（差分が追いやすい）

B) ワークフローのパッチ生成関数（必須）
- 関数（例）: build_ltx_i2v_workflow(params) -> dict(JSON)
- params に含めること：
  - input_image_path（プロジェクト側のパス）
  - positive_prompt / negative_prompt
  - width, height（32の倍数に正規化するか、エラーにするかを方針決めて実装）
  - frames（8n+1の制約に合わせる：正規化 or エラー）
  - steps, cfg, seed, fps, output_prefix
  - text_encoder_name（t5xxl_fp16 or fp8）
  - checkpoint_name（ltx-video-2b-v0.9.5.safetensors）
- JSONパッチは「node id をキーに widgets_values を上書き」でよい（テンプレ準拠）。
- 既存のプロジェクトに “ワークフローの変数展開（テンプレ埋め）”仕組みがあるなら、それを使う。

C) ComfyUI実行ラッパ（既存があれば再利用）
- 実行フロー：
  1. 入力画像を ComfyUI に渡す（次のどちらか）
     (a) ComfyUIの /upload/image にPOSTして input に置く
     (b) ComfyUIの input ディレクトリへコピー（同一マシンで共有FSの場合）
  2. /prompt に workflow(JSON) をPOSTして prompt_id を取得
  3. /history/{prompt_id} をポーリング（または /ws で進捗監視）
  4. 出力（webm）を取得：
     - 同一FSなら ComfyUI/output の該当ファイルをプロジェクトの成果物フォルダへコピー
     - 別ホストなら /view でダウンロードして保存
  5. 成果物メタデータ（prompt、seed、設定、テンプレバージョン、ComfyUI URL 等）をjsonで保存

D) ワークフロー登録（プロジェクト側のUI/CLI/ジョブに出るように）
- workflow_id 例: "ltx_i2v_simple_v0_9_5"
- display_name 例: "LTX I2V (0.9.5 / start image)"
- capability: image->video
- required_models: checkpoint + text_encoder
- default_params: width=768 height=512 frames=97 steps=30 cfg=3 fps=24 など（既存流儀に合わせる）

E) ドキュメント/README追記（必須）
- モデルの置き場所、ComfyUI起動方法、実行例（CLI/API）を追記
- “ハマりどころ”：
  - width/height は 32 の倍数
  - frames は 8n+1（例 65/97/257）
  - 出力は webm（SaveWEBM）
  - prompt は長い方が良い（LTXの特性）

# 出力形式（LLMの回答ルール）
- まず「検出した既存構造」と「追加方針（最小差分）」を短く要約
- 次に「変更ファイル一覧」を出す
- その後「unified diff 形式のパッチ」を提示（可能な限り）
- 最後に「実行手順（コマンド例）」と「期待される成果物パス」を書く
- 不明点があっても質問で止まらない。合理的に仮定して進め、仮定は明記する。
