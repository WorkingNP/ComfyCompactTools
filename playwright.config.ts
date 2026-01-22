import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E テスト設定
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // テストディレクトリ
  testDir: './tests/e2e',

  // 各テストのタイムアウト
  timeout: 30 * 1000,

  // テスト失敗時のリトライ回数
  retries: 0,

  // 並列実行数（CPUコア数に応じて調整）
  workers: 1,

  // レポーター設定
  reporter: [
    ['list'],
    ['html', { open: 'never' }]
  ],

  // 全テスト共通の設定
  use: {
    // ベースURL（FastAPIサーバー）
    baseURL: 'http://127.0.0.1:8787',

    // スクリーンショット（失敗時のみ）
    screenshot: 'only-on-failure',

    // トレース（失敗時のみ）
    trace: 'on-first-retry',

    // ビューポートサイズ
    viewport: { width: 1280, height: 720 },
  },

  // ブラウザ設定
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // 必要に応じて他のブラウザを追加
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // テスト前にサーバーを起動（オプション）
  // webServer: {
  //   command: 'python -m uvicorn server.main:app --host 127.0.0.1 --port 8787',
  //   url: 'http://127.0.0.1:8787',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000,
  // },
});
