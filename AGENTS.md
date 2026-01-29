# Agent Instructions

- When you need image generation, workflow listing, parameter discovery, or batch generation, use the comfy_cockpit MCP server tools first.
- For image generation requests, submit jobs with wait=false and do not block on completion.

# Project rules (ComfyCompactTools)

## Planning (mandatory)
- For any non-trivial change (UI changes, workflow additions, MCP/server changes, refactors):
  1) Create a plan file under `plans/` using `plans/_TEMPLATE.md`.
  2) Do not implement until the plan is written and the DoD (Bronze/Silver/Gold) is explicit.
  3) The plan MUST include a Phase 1 "Tests (RED)" section. No "tests later" for required behaviors.

## Subagents
- Use the `planner` agent to draft/structure plans.
- Use the `tdd-guide` agent to design and write tests first (Red → Green → Refactor).
- Use the `e2e-runner` agent for critical UI flows (Agent Browser preferred) and to capture artifacts.
