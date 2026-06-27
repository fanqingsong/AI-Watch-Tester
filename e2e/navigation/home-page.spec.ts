import { test, expect } from '@playwright/test';
import { APP_URL, skipIfAppDown } from '../helpers';

test.describe('Navigation and Basic Access', () => {
  test.beforeAll(async () => {
    await skipIfAppDown();
  });

  test('Home page access and navigation to all pages', async ({ page }) => {
    // 1. Navigate to home page and verify basic elements
    await page.goto(`${APP_URL}/`);
    
    // Verify page title contains 'Vibe-Trading'
    await expect(page).toHaveTitle(/Vibe-Trading/);
    
    // Verify hero heading is visible
    await expect(page.getByRole('heading', { name: 'AI-Powered Quant Strategy Research' })).toBeVisible();
    
    // Verify all navigation links exist
    await expect(page.getByRole('link', { name: 'Home' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Agent' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Alpha Zoo' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Correlation Matrix' })).toBeVisible();
    
    // 2. Click Agent nav link → verify URL becomes /agent and chat interface is visible
    await page.getByRole('link', { name: 'Agent' }).click();
    await expect(page).toHaveURL(/\/agent/);
    await expect(page.getByRole('heading', { name: 'Vibe-Trading' })).toBeVisible();
    await expect(page.getByPlaceholder('e.g. Create a dual MA crossover strategy for 000001.SZ, backtest 2024')).toBeVisible();
    
    // 3. Click Alpha Zoo nav link → verify URL becomes /alpha-zoo and the alpha catalogue displays
    await page.getByRole('link', { name: 'Alpha Zoo' }).click();
    await expect(page).toHaveURL(/\/alpha-zoo/);
    await expect(page.getByRole('heading', { name: '452 pre-built quant alphas across 4 zoos' })).toBeVisible();
    await expect(page.getByRole('table', { name: 'Alpha catalogue' })).toBeVisible();
    
    // 4. Click Settings nav link → verify URL becomes /settings
    await page.getByRole('link', { name: 'Settings' }).click();
    await expect(page).toHaveURL(/\/settings/);
    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();
    
    // 5. Click Correlation Matrix nav link → verify URL becomes /correlation
    await page.getByRole('link', { name: 'Correlation Matrix' }).click();
    await expect(page).toHaveURL(/\/correlation/);
    await expect(page.getByRole('heading', { name: 'Correlation Matrix' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'BTC-USDT,ETH-USDT,SPY' })).toBeVisible();
  });
});