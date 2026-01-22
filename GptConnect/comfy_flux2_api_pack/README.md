# ComfyUI ローカルAPIで FLUX.2 を回すパック（dev / klein 4B FP8）

このフォルダは「ComfyUI をキャンバス操作せずに」ローカルAPI（`/prompt`）だけで FLUX.2 を画像生成するための最小構成です。

含まれるもの
- `comfy_flux2_generate.py` : FLUX.2 dev 用（Mistral text encoder / flux2_dev / flux2-vae）
- `comfy_flux2_klein_generate.py` : FLUX.2 [klein] 4B FP8 用（Qwen3 text encoder / klein / flux2-vae）
- `flux2_dev_prompt_template.json` : dev の API prompt テンプレ（ノード接続済みグラフ）
- `flux2_klein_4b_fp8_prompt_template.json` : klein 4B distilled FP8 の API prompt テンプレ
- `flux2_klein_base_4b_fp8_prompt_template.json` : klein 4B base FP8 の API prompt テンプレ（任意）
- `tests/` : 実際に ComfyUI を叩いて画像が出たことを検証するE2Eテスト（pytest）

前提
- ComfyUI が起動していて、HTTP API が `http://127.0.0.1:8188` で待っている（変更する場合は `COMFY_BASE_URL` を設定）
- 各モデルファイルが ComfyUI の所定フォルダに配置済み
  - dev: `models/text_encoders/` `models/diffusion_models/` `models/vae/`
  - klein: `models/text_encoders/` `models/diffusion_models/` `models/vae/`

まず動かす（手動で1枚生成）
```bash
pip install -r requirements.txt

# FLUX.2 dev
python comfy_flux2_generate.py --prompt "a studio photo of a red robot" --out ./outputs_dev

# FLUX.2 klein 4B distilled FP8
python comfy_flux2_klein_generate.py --template flux2_klein_4b_fp8_prompt_template.json   --prompt "a hedgehog wearing a tiny party hat, 2000s digicam vibe" --out ./outputs_klein
```

テスト（画像が本当に出ることを確認）
```bash
pytest -q
```

- デフォルトでは「dev」と「klein distilled」のE2Eが走ります。
- `klein base FP8` のテストも回したい場合：
```bash
RUN_KLEIN_BASE_TESTS=1 pytest -q
```

モデル名を変えたい場合（環境変数）
- `FLUX2_DEV_TEXT_ENCODER` / `FLUX2_DEV_UNET` / `FLUX2_VAE`
- `KLEIN_TEXT_ENCODER` / `KLEIN_UNET_DISTILLED_FP8` / `KLEIN_UNET_BASE_FP8`

例:
```bash
FLUX2_DEV_UNET="flux2_dev_fp8mixed.safetensors" pytest -q
```

ローカルLLMにレビュー＆修正させる場合
- `FOR_LOCAL_LLM.md` をそのままローカルLLMに貼り付けて、フォルダごと渡してください。
