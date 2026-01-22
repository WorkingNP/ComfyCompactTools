# TICKET: HelloWorld表示ボタン

## Goal
- UIに「HelloWorld」ボタンを追加し、クリックするとユーザーに分かりやすく “Hello, world!” を表示できる。

## Non-goals
- 既存のUI構造の大改修
- 新しいUIライブラリの導入
- i18n/多言語対応の全面実装（必要なら最小限）

## User Journey
1. ユーザーがアプリを開く
2. スクロールなしで見える場所に「HelloWorld」ボタンがある
3. クリックすると “Hello, world!” が表示される（toast/ダイアログ/パネルなど既存流儀に合わせる）
4. 表示は閉じられる（または一定時間で消える）

## Acceptance Criteria
- 「HelloWorld」ボタンが UI 上に存在する
- クリックで “Hello, world!” が表示される
- 表示は閉じられる/邪魔にならない（デモで全画面縦スクロール必須にならない）
- 既存の主要機能を壊さない（既存テストが落ちない）

## Constraints
- 変更範囲は最小
- 新規依存は追加しない
- a11y: `role=button` で取得できる（または `data-testid` を付与）

## Test Plan
- Playwright の e2e テストで合否判定する（例：`tests/e2e/helloworld-button.spec.ts`）
- セレクタは優先順：`getByRole` → `getByTestId` → `locator`（CSSは最後の手段）
- web-first assertions を使う（`toBeVisible` など）

## Notes / Unknowns
- ボタンを置く“正しい場所”は現状のUIを見て決める（既存のツールバー/サイドパネル等に合わせる）
