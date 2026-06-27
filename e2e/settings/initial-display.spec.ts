import { test, expect } from '@playwright/test';

test.describe('Settings Page Basic Display', () => {
  test('Settings sections and LLM provider fields display', async ({ page }) => {
    // 1. Navigate to /settings and verify the 'Settings' heading is displayed
    await page.goto('http://127.0.0.1:8899/settings');

    // Verify the Settings heading is displayed
    await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();

    // 2. Verify the three main sections are visible as headings
    await expect(page.getByRole('heading', { name: 'Local API access' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'LLM Settings' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Data Source Settings' })).toBeVisible();

    // 3. In the LLM Settings section verify the 'Provider' dropdown, 'Model' textbox, 'Base URL' textbox, and 'API key' textbox are visible
    // Verify Provider dropdown
    await expect(page.getByRole('combobox', { name: /provider/i })).toBeVisible();

    // Verify Model textbox
    await expect(page.getByRole('textbox', { name: /model/i })).toBeVisible();

    // Verify Base URL textbox
    await expect(page.getByRole('textbox', { name: /base url/i })).toBeVisible();

    // Verify API key textbox (LLM section — disambiguate from the "Server API key" field by placeholder)
    await expect(page.getByPlaceholder('Leave blank to keep the current key')).toBeVisible();

    // 4. Verify the 'Use provider defaults' button is visible
    await expect(page.getByRole('button', { name: /use provider defaults/i })).toBeVisible();
  });
});