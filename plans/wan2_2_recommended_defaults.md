# ExecPlan: Wan2.2 TI2V defaults + prompt presets
- Date: 2026-01-30
- Owner: souto
- Status: Draft
- Related: plans/_TEMPLATE.md

## 1. Background / Context
- Update wan2_2_ti2v_5b manifest defaults to official recommended values.
- Add simple manual (wan22manual.md) listing recommended settings.
- Add default positive/negative prompt presets (user requested quality tags).

## 2. Goals
- [ ] Manifest defaults match official Wan2.2 TI2V template values (res/length/fps/steps/cfg/sampler/scheduler).
- [ ] Default positive/negative prompt presets are present in manifest.
- [ ] Manual file lists recommended settings and prompt presets.

## 3. Non-goals
- UI redesign or new workflow types.
- Changing server behavior beyond defaults.

## 4. Touch points
### Workflows
- workflows/wan2_2_ti2v_5b/manifest.json
- workflows/wan2_2_ti2v_5b/template_api.json (only if alignment needed)

### Tests
- server/tests/test_api_integration.py

### Docs
- wan22manual.md

## 5. Approach
- Use official ComfyUI Wan2.2 TI2V template defaults for numeric settings.
- Add user-requested quality prompt presets (masterpiece / bad anatomy, etc.).
- Keep changes minimal and documented.

## 6. Phases
### Phase 1: Tests (RED)
- [ ] Add integration test to assert wan2_2_ti2v_5b defaults from /api/workflows/{id}.
- [ ] Assert prompt/negative defaults match expected strings.

### Phase 2: Implementation (GREEN)
- [ ] Update manifest defaults to recommended values.
- [ ] Add prompt/negative defaults to manifest.
- [ ] Align template_api.json if needed.

### Phase 3: Refactor
- [ ] Keep strings/constants tidy in tests.

### Phase 4: Docs
- [ ] Add wan22manual.md with recommended settings list.

## 7. DoD
### Bronze
- [ ] /api/workflows/wan2_2_ti2v_5b returns recommended defaults.
- [ ] Manual file exists with settings list.

### Silver
- [ ] Tests for defaults pass.

### Gold
- [ ] Optional full test run passes (pytest -m "not e2e").

## 8. Risks / Mitigations
- Defaults may be heavy for some GPUs -> document as recommended, not mandatory.

## 9. Rollback
- Revert manifest defaults and remove wan22manual.md.
