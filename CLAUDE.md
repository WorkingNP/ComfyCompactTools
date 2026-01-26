# Claude Code 指示書：ComfyCompactTools を “テンプレJSON + マニフェスト駆動” にリファクタする

あなたは Claude Code（コード編集・実装担当）です。  
このリポジトリを、**固定ワークフロー依存**から脱却させ、将来の拡張（Flux系、ControlNet、xyz plot 等）に耐える形へ整えます。

---

## 最重要ルール（破ったらやり直し）

1. **実装修正の前にテストを書く**
- まず現状の振る舞いをテストで固定してください。
- 次に「このリファクタで守りたい仕様」をテストに追加してください。
- そのテストが通るまで、実装を繰り返し修正してください。

2. **テンプレJSON（Comfy API prompt JSON）をファイル上で編集しない**
- テンプレは読み取り専用です。
- 実行時に template を読み込み、deep copy したオブジェクトに対してパッチを当てて送ってください。
- ファイルを書き換える方式は、副作用の温床です（並列実行、途中クラッシュ、テンプレ汚染）。

3. 既存機能を壊さない（後方互換を優先）
- 既存のUI/API/DB/ギャラリーがあるなら、まず壊さない。
- どうしてもAPIの仕様を変えるなら、移行ルート（互換エンドポイント、互換フィールド）を用意する。

---

## 背景（あなたがリポジトリを読んで確認すること）

このリポジトリは、ローカルComfyUIを叩いて画像生成する “コックピット” のMVPです。  
現状は「固定のワークフロー（例: SD txt2img）」に強く依存しているはずです。

リポジトリ直下には例として `templates.json` があり、モデルごとのpresetが並んでいます。  
また、Flux用のAPIテンプレやスクリプトが入っているフォルダが存在する可能性があります。  
（このあたりは、あなたが実際のファイルを読んで確定してください。）

---

## このリファクタのゴール（要約）

- “ワークフロー差分” を **コードではなくデータ**で吸収する  
  → ワークフローは **テンプレJSON + マニフェスト**で追加できるようにする
- パラメータ変更は **テンプレdeep copyにパッチ**して送るだけにする
- テストが増えて、追加ワークフローが安全にできるようになる
- 将来の xyz plot / controlnet / i2i の追加で破綻しない土台になる

詳細は `docs/01_goals_and_non_goals.md` と `docs/02_architecture.md` を参照。

---

## 必須アウトプット（完了条件）

1. 新しい概念：Workflow Registry（ワークフロー登録機構）
- `workflow_id` でワークフローを選択できる
- ワークフローはディレクトリ（例: `workflows/<id>/`）にまとまっている
- その中に
  - `template_api.json`（ComfyUIへ送るAPI prompt）
  - `manifest.json`（入力定義 + patch map）
  がある（名前は多少変えてもよいが、概念を分けること）

2. サーバ/実行側が workflow_id + params を受け取って動く
- 既存のジョブ投入の入口があるなら、そこに `workflow_id` を追加する（互換も維持）
- 内部で manifest に従って params を検証し、テンプレdeep copyにパッチして ComfyUIへ投げる

3. テスト群
- Unit tests（ComfyUI不要）: マニフェスト/パッチ/画像白黒チェック
- Integration tests（HTTPモック）: エラー処理・タイムアウト・レスポンス解析
- E2E tests（ComfyUI起動時のみ）: 実際に画像が出る + 白黒判定
- `pytest` が通ること（ComfyUI無しでも unit+integration は通る）

---

## 実装ステップ（この順で進めてください）

### Step 0: 現状把握
- まず `pytest -q` を実行し、現在あるテストと失敗点を把握する
- 既存の “ジョブ作成→ComfyUI→画像保存→ギャラリー” の流れをコードから追う
- 「固定ワークフロー依存」がどの層にあるかを特定する
  - 例: workflow JSONをコードで組み立てている
  - 例: 特定ノードIDを直書きしている
  - 例: UIが特定パラメータだけ送っている など

### Step 1: Unit tests を先に追加する（実装を触る前）
追加すべきテストは `docs/04_test_plan.md` を参照。

最低限:
- manifest のロード/バリデーション
- template deep copy の純粋性（元が変化しない）
- patch適用の正しさ
- 画像白黒チェック（黒/白/単色/ノイズ）

この時点では「まだWorkflow Registryは無くてよい」  
“これから作る関数/クラス” を想定してテストを書き、最初は failing にしてよい（テストファースト）。

### Step 2: Workflow Registry を作る（最小）
- `workflows/` ディレクトリを読み、利用可能な workflow を列挙する機構を作る
- `manifest.json` と `template_api.json` をロードできるようにする
- バリデーションを入れる
  - manifestに必須フィールドがある
  - template_path が存在する
  - patch target の node_id/field がテンプレ内に存在するか（できれば）

### Step 3: Patcher（テンプレにパッチを当てる純粋関数）
- 入力: template_dict, manifest, params
- 出力: patched_template_dict（deep copy済み）
- 実装のポイント:
  - deep copy を必ず行う（元を壊さない）
  - field指定（例: `"inputs.seed"`）を安全に辿って set する
  - 型変換/範囲チェックは manifest に基づいて行う
  - 失敗時は “どのparam / どのnode_id / どのfield” で落ちたか分かる例外にする

### Step 4: サーバ側のジョブ投入を workflow_id 対応にする
- 既存の job create があるなら:
  - 互換のため、workflow_id が無ければ “従来のデフォルト” を使う
  - workflow_id があれば registry からテンプレ+manifest を取って実行する
- 可能なら新規で
  - `GET /api/workflows`（利用可能workflow一覧）
  - `GET /api/workflows/{id}`（manifest）
  を追加する（UIの動的フォーム生成に必要）

### Step 5: E2E（ComfyUI起動時）で本当に生成できることを確認
- 成功が確実なワークフロー（例: Flux.2 klein distilled）を1つ以上、必須E2Eにする
- 画像が保存されていること
- 画像の白黒チェックに通ること

注意:
- Flux.2 dev のように “モデル側都合で黒が出る” ものは、E2Eの必須から外す/xfail/skip などで管理すること。
- それでも “生成自体は通る” ことを確認したい場合は、白黒チェックを弱める（manifestのquality_checks）か、
  “smoke test” として別カテゴリに切る。

### Step 6: ドキュメント更新
- READMEまたは docs に「新しいワークフローを追加する手順」を追加
  - テンプレJSONの作り方（ComfyUIのSave API Format）
  - manifest の書き方
  - presets の扱い（任意）
  - テストの追加方法

---

## 実装上の注意（地雷回避）

- **固定フォーム地獄を避ける**
  - UIは manifest をもとに動的フォーム生成するのが正攻法。
  - 最初は “paramを羅列して input を作るだけ” の素朴実装でOK。
- **例外メッセージをケチらない**
  - ComfyUIは失敗理由が分かりにくいことがある。
  - こちら側は “どのworkflow / どのnode / どのinput” かをログに残す。
- **依存追加は慎重に**
  - pydantic等は便利だが、既存依存との整合を確認。
  - 追加するなら「なぜ必要か」を短く書き残す。
- ローカルのブラウザアプリUIに変更を加えるタスクでは、必ずスクリーンショットを撮って見た目を確認し、違和感や不具合があれば報告すること。

---

## 参照資料

- `docs/01_goals_and_non_goals.md`
- `docs/02_architecture.md`
- `docs/03_manifest_spec.md`
- `docs/04_test_plan.md`
- `docs/05_future_features_xyz_controlnet.md`
- `docs/manifest.schema.json`
- `docs/examples/`

---

## 最後に（作業レポートに必ず書くこと）

あなたの作業完了時に、以下を短くまとめてください:

- 何を追加/変更したか（ファイル単位）
- 新しいワークフロー追加手順（3〜5行）
- `pytest` の実行結果（Comfy無しで通る範囲 / Comfy起動時のE2E）
