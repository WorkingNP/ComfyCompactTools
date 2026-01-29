# ExecPlan: Gallery manual refresh + pagination
- Date: 2026-01-29
- Owner: codex
- Status: Draft
- Related: UI performance / gallery freeze

## 1. Context / Problem
- Gallery auto-updates on every WS asset event, causing heavy UI redraws and browser stalls.
- Thumbnails can appear squashed; gallery can show too many items at once.
- Goal is manual refresh + capped visible items to reduce UI load.

## 2. Goals
- [ ] Gallery previews update only when user clicks Refresh.
- [ ] Thumbnails keep aspect ratio (no visible squashing).
- [ ] Show max 9 items per page with simple navigation.

## 3. Non-goals
- No server/MCP protocol changes.
- No workflow/template changes.

## 4. Touch points
### UI
- web/index.html
- web/app.js
- web/styles.css

## 5. Approach
- Add gallery toolbar controls: Refresh + Prev/Next + page indicator.
- Track gallery dirty state and last-render count; render gallery only on manual refresh.
- Slice assets per page (page size 9), clamp page index.
- Enforce square card aspect ratio to avoid squashing.

## 6. Phases
### Phase 0: Read only
- [x] Inspect gallery render + WS update flow.
- [x] Inspect gallery toolbar + CSS.

### Phase 1: Tests (RED)
- Manual:
  - [ ] With active WS updates, gallery does not change until Refresh is clicked.
  - [ ] Refresh updates gallery and clears “dirty” indicator.
  - [ ] Prev/Next shows different pages and never exceeds 9 items/page.
  - [ ] Thumbnails render without visible squashing.

### Phase 2: Implement (GREEN)
- [ ] Add toolbar controls and handlers.
- [ ] Gate gallery renders behind manual refresh.
- [ ] Add pagination slice + page indicator.
- [ ] Update gallery card CSS for stable aspect ratio.

### Phase 3: Refactor
- [ ] Keep render/schedule logic simple; avoid extra renders.

## 7. DoD
### Bronze
- [ ] Manual refresh works; auto WS updates do not repaint gallery.
- [ ] 9-per-page pagination works with Prev/Next.
- [ ] Thumbnails are not squashed.

### Silver
- [ ] Dirty indicator shows when new assets arrive.

### Gold
- [ ] No noticeable UI jank when jobs are streaming in.
