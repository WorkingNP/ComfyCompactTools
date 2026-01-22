import { test, expect } from '@playwright/test';

/**
 * HelloWorld表示ボタン：受け入れテスト（テンプレ）
 *
 * TODO:
 * - baseURL / 起動方法はプロジェクトに合わせて設定
 * - セレクタ（role名 / testid）を実装に合わせて確定
 */
test('HelloWorld button shows "Hello, world!"', async ({ page }) => {
  // TODO: アプリのURL（または baseURL）に合わせる
  await page.goto('/');

  // 1) ボタンが見える
  const btn = page.getByRole('button', { name: /helloworld/i });
  await expect(btn).toBeVisible();

  // 2) クリックでメッセージが出る
  await btn.click();
  await expect(page.getByText(/hello, world!/i)).toBeVisible();

  // 3) 閉じられる（ダイアログの場合の例）
  // TODO: 実装に合わせる（toastなら不要）
  // const close = page.getByRole('button', { name: /close|閉じる/i });
  // await close.click();
  // await expect(page.getByText(/hello, world!/i)).toBeHidden();
});
