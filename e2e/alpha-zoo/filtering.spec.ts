import { test, expect } from '@playwright/test';

const URL = 'http://127.0.0.1:8899/alpha-zoo';

test.describe('Alpha Zoo Filtering', () => {
  test('Alpha zoo search and dropdown filtering', async ({ page }) => {
    await page.goto(URL);

    // Page loads with the catalogue heading and table
    await expect(
      page.getByRole('heading', { name: '452 pre-built quant alphas across 4 zoos' })
    ).toBeVisible();
    const table = page.getByRole('table', { name: 'Alpha catalogue' });
    await expect(table).toBeVisible();

    // 1. Search box filters by id/nickname: use a known alpha id
    const searchInput = page.getByPlaceholder('Filter by id or nickname…');
    await searchInput.fill('alpha101_001');
    await expect(table.getByRole('link', { name: 'alpha101_001' })).toBeVisible();
    await searchInput.fill('');

    // 2. Zoo dropdown: select "Qlib 158" — only Qlib alphas remain
    const zooCombo = page.getByRole('combobox', { name: 'Zoo' });
    await zooCombo.selectOption('Qlib 158');
    await expect(table.getByRole('cell', { name: 'qlib158', exact: true }).first()).toBeVisible();
    await expect(table.getByRole('cell', { name: 'alpha101', exact: true })).toHaveCount(0);
    await zooCombo.selectOption('All zoos');

    // 3. Theme dropdown: select "momentum" — visible rows carry the momentum theme
    const themeCombo = page.getByRole('combobox', { name: 'Theme' });
    await themeCombo.selectOption('momentum');
    await expect(table.getByRole('cell', { name: 'momentum', exact: true }).first()).toBeVisible();
  });
});
