// spec: Correlation Matrix Display
// seed: http://127.0.0.1:8899/correlation

import { test, expect } from '@playwright/test';
import { APP_URL, skipIfAppDown } from '../helpers';

test.describe('Correlation Matrix Display', () => {
  test.beforeAll(async () => {
    await skipIfAppDown();
  });

  test('Correlation matrix input controls display', async ({ page }) => {
    // Step 1: Navigate to /correlation and verify the 'Correlation Matrix' heading is displayed
    await page.goto(`${APP_URL}/correlation`);
    
    // Verify the Correlation Matrix heading is displayed
    await expect(page.getByRole('heading', { name: 'Correlation Matrix', level: 1 })).toBeVisible();

    // Step 2: Verify the asset codes label and its textbox with default value
    await expect(page.getByText('Asset codes', { exact: true })).toBeVisible();
    // The /correlation page has a single textbox; its accessible name is its value
    const assetCodesTextbox = page.getByRole('textbox');
    await expect(assetCodesTextbox).toHaveValue('BTC-USDT,ETH-USDT,SPY,AAPL');

    // Step 3: Verify window buttons are visible (30d, 60d, 90d, 180d, 365d)
    await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
    await expect(page.getByRole('button', { name: '60d' })).toBeVisible();
    await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    await expect(page.getByRole('button', { name: '180d' })).toBeVisible();
    await expect(page.getByRole('button', { name: '365d' })).toBeVisible();

    // Step 4: Verify method buttons are visible (pearson, spearman)
    await expect(page.getByRole('button', { name: 'pearson' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'spearman' })).toBeVisible();

    // Step 5: Verify the Compute button is visible
    await expect(page.getByRole('button', { name: 'Compute' })).toBeVisible();
  });
});
