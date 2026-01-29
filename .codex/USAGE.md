# GPT Codex 菴ｿ逕ｨ繧ｬ繧､繝・
縺薙・繝励Ο繧ｸ繧ｧ繧ｯ繝医〒GPT Codex繧剃ｽｿ逕ｨ縺吶ｋ髫帙・繧ｬ繧､繝峨〒縺吶・
## 蜑肴署譚｡莉ｶ

- MCP邨檎罰縺ｧCodex繝・・繝ｫ縺悟茜逕ｨ蜿ｯ閭ｽ縺ｧ縺ゅｋ縺薙→
- Claude Code迺ｰ蠅・〒螳溯｡後☆繧句ｴ蜷医・縲｀CP繝励Λ繧ｰ繧､繝ｳ `codex` 縺梧怏蜉ｹ縺ｫ縺ｪ縺｣縺ｦ縺・ｋ縺薙→

---

## 蝓ｺ譛ｬ逧・↑菴ｿ縺・婿

### 1. 繝ｫ繝ｼ繝ｫ繧定ｪｭ縺ｿ霎ｼ繧薙〒繧ｻ繝・す繝ｧ繝ｳ髢句ｧ・
```python
# Python邨檎罰縺ｮ萓・with open(".codex/rules/all-rules.md") as f:
    rules = f.read()

mcp__codex__codex({
    "prompt": "SDXL txt2img繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ縺ｮmanifest縺ｫcheckpoint驕ｸ謚槭ｒ霑ｽ蜉縺励※",
    "base-instructions": rules,
    "cwd": ".",
    "sandbox": "workspace-write",
    "approval-policy": "on-failure"
})
```

### 2. 繝励Ο繝輔ぃ繧､繝ｫ繧剃ｽｿ縺｣縺溯ｵｷ蜍包ｼ域耳螂ｨ・・
縺ｾ縺・`config.toml` 繧剃ｽ懈・・・
```toml
[profile.grok-comfy]
model = "gpt-5.2-codex"
sandbox = "workspace-write"
approval-policy = "on-failure"
cwd = "."
```

襍ｷ蜍墓凾縺ｫ繝励Ο繝輔ぃ繧､繝ｫ謖・ｮ夲ｼ・
```python
mcp__codex__codex({
    "prompt": "SDXL txt2img繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ縺ｮmanifest縺ｫcheckpoint驕ｸ謚槭ｒ霑ｽ蜉縺励※",
    "profile": "grok-comfy"
})
```

### 3. 繧ｻ繝・す繝ｧ繝ｳ邯咏ｶ・
```python
# threadId繧剃ｿ晏ｭ倥＠縺ｦ縺翫￥
thread_id = "蜑榊屓縺ｮ繧ｻ繝・す繝ｧ繝ｳ縺ｧ霑斐＆繧後◆ID"

mcp__codex__codex_reply({
    "threadId": thread_id,
    "prompt": "谺｡縺ｯVAE驕ｸ謚槭ｂ霑ｽ蜉縺励※"
})
```

---

## 繧医￥縺ゅｋ繧ｿ繧ｹ繧ｯ萓・
### ComfyUI繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ螳溯｣・
```python
mcp__codex__codex({
    "prompt": """
譁ｰ縺励＞Flux img2img繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ繧貞ｮ溯｣・＠縺ｦ縺上□縺輔＞縲・- workflows/flux_img2img/ 繝・ぅ繝ｬ繧ｯ繝医Μ繧剃ｽ懈・
- manifest.json 縺ｨ template.json 繧剃ｽ懈・
- 繝・せ繝医ｂ荳邱偵↓菴懈・
    """,
    "base-instructions": open(".codex/rules/all-rules.md").read(),
    "sandbox": "workspace-write"
})
```

### 繝・せ繝郁ｿｽ蜉

```python
mcp__codex__codex({
    "prompt": """
server/model_scanner.py 縺ｫ蟇ｾ縺吶ｋ蜊倅ｽ薙ユ繧ｹ繝医ｒ霑ｽ蜉縺励※縺上□縺輔＞縲・.codex/rules/testing-guidelines.md 縺ｮ繝√ぉ繝・け繝ｪ繧ｹ繝医↓蠕薙≧縺薙→縲・    """,
    "developer-instructions": "蠢・★ .codex/rules/testing-guidelines.md 繧貞盾辣ｧ縺吶ｋ縺薙→",
    "sandbox": "workspace-write"
})
```

### 繧ｳ繝ｼ繝峨Ξ繝薙Η繝ｼ

```python
mcp__codex__codex({
    "prompt": "server/main.py 縺ｮ繧ｳ繝ｼ繝峨Ξ繝薙Η繝ｼ繧貞ｮ滓命縺励※縺上□縺輔＞",
    "sandbox": "read-only",  # 隱ｭ縺ｿ蜿悶ｊ蟆ら畑縺ｧ繝ｬ繝薙Η繝ｼ
    "approval-policy": "never"
})
```

---

## 繝ｫ繝ｼ繝ｫ繝輔ぃ繧､繝ｫ縺ｮ菴ｿ縺・・縺・
| 繝輔ぃ繧､繝ｫ | 菴ｿ逕ｨ繧ｿ繧､繝溘Φ繧ｰ |
|---------|--------------|
| `all-rules.md` | 豎守畑逧・↑繧ｿ繧ｹ繧ｯ蜈ｨ闊ｬ・域耳螂ｨ・・|
| `main.md` | 繝励Ο繧ｸ繧ｧ繧ｯ繝亥渕譛ｬ繝ｫ繝ｼ繝ｫ縺ｮ縺ｿ蠢・ｦ√↑蝣ｴ蜷・|
| `comfy-workflow-rules.md` | ComfyUI繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ髢｢騾｣縺ｮ繧ｿ繧ｹ繧ｯ髯仙ｮ・|
| `testing-guidelines.md` | 繝・せ繝井ｽ懈・繝ｻ繝ｬ繝薙Η繝ｼ髯仙ｮ・|
| `ui-testing-with-agent-browser.md` | UI繝・せ繝磯剞螳・|

---

## 繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ

### 繝ｫ繝ｼ繝ｫ縺悟渚譏縺輔ｌ縺ｪ縺・
`base-instructions` 繝代Λ繝｡繝ｼ繧ｿ縺ｧ繝ｫ繝ｼ繝ｫ繝輔ぃ繧､繝ｫ縺ｮ蜀・ｮｹ繧呈枚蟄怜・縺ｨ縺励※貂｡縺吝ｿ・ｦ√′縺ゅｊ縺ｾ縺呻ｼ・
```python
# 笶・繝繝｡縺ｪ萓・mcp__codex__codex({
    "base-instructions": ".codex/rules/all-rules.md"  # 繝代せ繧呈ｸ｡縺励※繧りｪｭ縺ｾ繧後↑縺・})

# 笨・濶ｯ縺・ｾ・with open(".codex/rules/all-rules.md") as f:
    mcp__codex__codex({
        "base-instructions": f.read()  # 繝輔ぃ繧､繝ｫ蜀・ｮｹ繧呈ｸ｡縺・    })
```

### 繧ｻ繝・す繝ｧ繝ｳ縺瑚ｦ九▽縺九ｉ縺ｪ縺・
`threadId` 繧呈ｭ｣縺励￥菫晏ｭ倥・蠑輔″邯吶℃縺励※縺・ｋ縺狗｢ｺ隱搾ｼ・
```python
# 譛蛻昴・繧ｻ繝・す繝ｧ繝ｳ
result = mcp__codex__codex({"prompt": "..."})
thread_id = result["threadId"]  # 縺薙ｌ繧剃ｿ晏ｭ・
# 邯咏ｶ・mcp__codex__codex_reply({
    "threadId": thread_id,  # 菫晏ｭ倥＠縺櫑D繧剃ｽｿ縺・    "prompt": "邯壹″繧偵♀鬘倥＞"
})
```

---

## Claude Code 縺ｨ縺ｮ菴ｿ縺・・縺・
| 逕ｨ騾・| 謗ｨ螂ｨ繝・・繝ｫ |
|-----|----------|
| 繧､繝ｳ繧ｿ繝ｩ繧ｯ繝・ぅ繝悶↑髢狗匱縲∬ｳｪ蝠上∵爾邏｢ | Claude Code |
| 繝励Λ繝ｳ繝九Φ繧ｰ縲√い繝ｼ繧ｭ繝・け繝√Ε險ｭ險・| Claude Code |
| 閾ｪ蜍募喧繧ｿ繧ｹ繧ｯ縲√ヰ繝・メ蜃ｦ逅・| GPT Codex |
| CI/CD邨ｱ蜷医√せ繧ｯ繝ｪ繝励ヨ螳溯｡・| GPT Codex |
| 繧ｳ繝ｼ繝峨Ξ繝薙Η繝ｼ・郁・蜍包ｼ・| GPT Codex |
| 繝・せ繝育函謌撰ｼ亥､ｧ驥擾ｼ・| GPT Codex |

