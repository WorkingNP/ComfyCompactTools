あなたはこのリポジトリに、Wan2.2 の i2v（画像→動画）ワークフローを追加します。
ComfyUI は起動中で、e2eも実行して動作確認まで完了させてください。

最重要ルール
- 変更前にテストを追加し、テストが通るまで修正を繰り返す（TDD）。
- `pytest -m "not e2e"` は ComfyUI無しでも常に緑。
- ワークフローテンプレJSONはファイルを直接編集しない。
  読み込み→メモリ上でコピー→パッチ→送信のみ。
- UIは workflow ごとの分岐を増やさず manifest 駆動を維持する。

今回の範囲
- 追加するのは i2v のみ（Fun Control や v2v はまだやらない）
- 出力は動画（mp4など）を assets として返し、UIで再生できるようにする

前提（ユーザー環境）
- ComfyUI Portable のルート（例）
  C:\Users\souto\Desktop\ComfyUI_windows_portable\ComfyUI
- ComfyUI の input フォルダ
  C:\Users\souto\Desktop\ComfyUI_windows_portable\ComfyUI\input
- ComfyUI の output フォルダ
  C:\Users\souto\Desktop\ComfyUI_windows_portable\ComfyUI\output
- ComfyUI のHTTP（既存設定に従う。一般的には http://127.0.0.1:8188 だが、プロジェクトで既に設定があるならそれを使う）
- このプロジェクトのサーバは http://127.0.0.1:8787 で動いている前提

必要モデル（ユーザーが配置済みであることを確認。無ければREADMEに手順を書く）
ComfyUI公式の Wan2.2 TI2V 5B の構成に合わせること。
- diffusion model: wan2.2_ti2v_5B_fp16.safetensors → ComfyUI/models/diffusion_models/
- VAE: wan2.2_vae.safetensors → ComfyUI/models/vae/
- text encoder: umt5_xxl_fp8_e4m3fn_scaled.safetensors → ComfyUI/models/text_encoders/

使う公式テンプレ（このJSONをリポジトリに保存し、常にこれをベースにパッチする）
- https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_wan2_2_5B_ti2v.json

ゴール（UI）
- workflow 選択に Wan2.2 i2v が出る（例: wan2_2_ti2v_5b）
- Parameters で変更できる
  - prompt / negative_prompt
  - width / height
  - length（frames）
  - fps
  - steps / cfg
  - sampler / scheduler
  - seed（randomize含む）
  - start_image（ファイル入力。必須）
- Generate でジョブ実行→完了→ギャラリーに動画が出て、クリックすると再生できる

実装タスク（順番厳守）

Task 1: failing test を追加（not e2e）
- GET /api/workflows に wan2_2_ti2v_5b が出る
- GET /api/workflows/{id} が manifest（フォーム生成に必要なschema）を返す
- manifest に image 入力型（start_image）が表現されること
  - 既存UIが file input を持っていない場合、このTaskでUI拡張まで含めてもよいが、
    まずはサーバ返却schemaを整えることを優先する

Task 2: workflow テンプレファイルをリポジトリに追加
- 例: workflows/templates/video_wan2_2_5B_ti2v.json のような位置（既存構造に合わせる）
- 以後は常にこのファイルを読み込む（ネットから毎回取得しない）

Task 3: manifest を追加（フォーム駆動）
- 既存の flux / sd1.5 の manifest と同じ形式で追加
- 型はUIが解釈できるものに揃える（string/integer/float/boolean/choices など）
- defaults は manifest を正とし、UI側ハードコードで上書きされないようにする
- 推奨デフォルト（e2eを軽くするため）
  - width: 640
  - height: 352（または 360）
  - length: 24〜32
  - fps: 12〜24
  - steps: 10〜15
  - cfg: 5
  - sampler/scheduler: 既存のsd1.5と同じ候補でよい
  - seed: randomize

Task 4: apply_patch 実装（not e2e）
- テンプレJSONを読み込んで dict にし、params を反映して ComfyUI に投げられる prompt JSON を生成する
- どのノードをパッチするかは、テンプレJSONを解析して決める
  - CLIPTextEncode（Positive/Negative）の widgets_values を prompt/negative_prompt で差し替え
  - Wan22ImageToVideoLatent の widgets_values を width/height/length で差し替え
  - CreateVideo の widgets_values を fps で差し替え
  - KSampler の seed/steps/cfg/sampler/scheduler を差し替え
  - LoadImage の filename を start_image_filename で差し替え
  - もし LoadImage が bypass されている（modeが 4 等）場合は、i2v専用ワークフローなので実行時に有効化する
- 追加パラメータが破棄されないこと（params dict をそのまま通す）をテストで固定

Task 5: 画像アップロード（start_image）対応（not e2e）
- UIから送るための方式を決める（推奨: 2段階）
  1) POST /api/uploads/image で multipart 受信し、ComfyUI/input に保存
     - 返り値: { filename }
  2) POST /api/jobs で start_image_filename を params に含めてジョブ作成
- テストでは tmp ディレクトリを ComfyUI/input の代わりにできるよう設定をDIする
  - 例: COMFYUI_DIR または COMFYUI_INPUT_DIR を追加
- not e2e では FakeComfyClient で prompt JSON が正しく組み立てられていることまで確認する

Task 6: 動画 outputs の取り回し（not e2e）
- ComfyUI の /history の outputs から、動画ファイル（mp4等）を検出して job outputs に含める
  - SaveImage の images と同様に、SaveVideo は videos（または類似キー）を返す可能性があるので両対応にする
- /assets/{filename} で mp4 を配信できるようにする（Content-Type含む）
- UIのギャラリーは、typeがvideo or 拡張子が mp4/webm の場合は <video controls> で表示

Task 7: e2e テスト（ComfyUI起動中で実行）
- `pytest -m e2e -k wan2_2_ti2v_5b` を追加し、実行して通す
- 入力画像はテスト内で小さなPNGを生成してアップロードしてよい
- 成功条件
  - job が completed
  - outputs に video が1つ以上
  - 追加の健全性チェック
    - 最低限: ファイルサイズが極小ではないこと（例: 50KB以上など）
    - 可能なら: 先頭フレーム抽出して単色判定（既存の not_blank 方式に寄せる）

Task 8: README更新
- 必要モデルと配置先
- COMFYUI_DIR（または input/output 設定）の指定方法
- i2vの使い方（UI手順）

完了条件
- `pytest -m "not e2e"` が緑
- `pytest -m e2e -k wan2_2_ti2v_5b` が通る（ComfyUI起動中）
- UIで start_image を選んで動画が生成され、ギャラリーで再生できる
