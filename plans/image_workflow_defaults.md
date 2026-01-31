# ExecPlan: Image workflow defaults (Flux2/SDXL/SD15)
- Date: 2026-01-30
- Owner: souto
- Status: Draft
- Related: plans/_TEMPLATE.md

## 1. Background / Context
- Align defaults for existing image workflows with official ComfyUI templates.
- Include positive/negative prompt defaults in manifests.

## 2. Goals
- [ ] flux2_klein_distilled defaults updated from official template (prompt + core params).
- [ ] sdxl_txt2img defaults updated from official template (prompt/negative + steps/cfg/sampler/scheduler).
- [ ] sd15_txt2img defaults updated from official template (prompt/negative + cfg).
- [ ] Tests cover new defaults via /api/workflows/{id}.

## 3. Non-goals
- Changing workflow graph structure or adding refiner stages.
- UI redesign.

## 4. Touch points
### Workflows
- workflows/flux2_klein_distilled/manifest.json
- workflows/sdxl_txt2img/manifest.json
- workflows/sd15_txt2img/manifest.json
- (optional) workflows/*/template_api.json for prompt defaults

### Tests
- server/tests/test_api_integration.py

## 5. Approach
- Use official ComfyUI workflow template package as source-of-truth for defaults.
- Update manifest defaults and presets; keep graph structure unchanged.

## 6. Phases
### Phase 1: Tests (RED)
- [ ] Add/adjust tests for flux2/sdxl/sd15 defaults (prompt/negative + key params).

### Phase 2: Implementation (GREEN)
- [ ] Update manifest defaults to match official templates.
- [ ] Update template_api.json prompt/negative text for consistency.

### Phase 3: Refactor
- [ ] Keep tests concise and aligned with defaults.

### Phase 4: Docs
- [ ] (Optional) Note default source in docs if needed.

## 7. DoD
### Bronze
- [ ] /api/workflows/{id} returns official defaults for flux2/sdxl/sd15.

### Silver
- [ ] Tests for defaults pass.

### Gold
- [ ] Full test run (not e2e) passes.

## 8. Risks / Mitigations
- Defaults may be heavier than current; keep workflow structure unchanged.

## 9. Rollback
- Revert manifest and template_api changes.

## 10. Plan closure
- Done:
  - [ ] ...
- Blocked:
  - [ ] ...
- Cancelled:
  - [ ] ...
