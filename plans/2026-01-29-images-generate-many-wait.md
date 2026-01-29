# ExecPlan: images_generate_many wait=false
- Date: 2026-01-29
- Owner: codex
- Status: Draft
- Related: MCP tool latency / UI freeze

## 1. Context / Problem
- images_generate_many always polls until all prompts complete.
- This blocks tool responses and causes UI stalls when sending many prompts.

## 2. Goals
- [ ] Add wait=false to images_generate_many to return job_ids immediately.
- [ ] Keep wait=true behavior unchanged (polls, returns outputs).
- [ ] Update tool schema + docs + tests.

## 3. Non-goals
- No UI changes.
- No workflow/manifest changes.

## 4. Touch points
### MCP / Server
- server/mcp_tools.py
- server/__main__.py
- server/tests/test_mcp_tools.py
- README.md (tool docs)

## 5. Approach
- Add wait param (default True) to images_generate_many.
- If wait=False: return results with job_id/status immediately, no polling.
- If wait=True: current polling path stays the same.

## 6. Phases
### Phase 1: Tests (RED)
- [ ] wait=False returns queued jobs with empty outputs (no timeout).
- [ ] wait=True can still return outputs when jobs complete.

### Phase 2: Implement (GREEN)
- [ ] Add wait param to images_generate_many signature/docstring.
- [ ] Update MCP tool schema + call path.
- [ ] Update tests with auto-complete fake client.
- [ ] Update README usage.

### Phase 3: Refactor
- [ ] Keep logic minimal; avoid duplicated polling code.

## 7. DoD
### Bronze
- [ ] wait=false returns job_id list without polling.
- [ ] wait=true still polls and returns outputs.
### Silver
- [ ] MCP tool schema documents wait.
### Gold
- [ ] Tests pass for both modes.
