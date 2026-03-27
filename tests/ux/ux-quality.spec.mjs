import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('UX Quality Gates', () => {
  test('landing shell has keyboard-first affordances', async ({ page }) => {
    await page.goto('/web/');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.skip-link')).toHaveAttribute('href', '#dashboard-root');
    await page.keyboard.press('Tab');
    await expect(page.locator('#auth-email')).toBeFocused();

    const liveDate = page.locator('#live-datetime');
    await expect(liveDate).toBeVisible();
    await expect(liveDate).not.toContainText('Loading');
    await expect(liveDate).toContainText('UTC');
  });

  test('no critical accessibility violations on initial shell', async ({ page }) => {
    await page.goto('/web/');
    await page.waitForLoadState('networkidle');

    const scan = await new AxeBuilder({ page })
      .exclude('#scene')
      .analyze();

    const criticalViolations = scan.violations.filter((violation) => violation.impact === 'critical');
    expect(criticalViolations).toEqual([]);
  });

  test('remedial online link input preserves faculty-entered URL', async ({ page }) => {
    await page.goto('/web/');
    await page.waitForLoadState('networkidle');

    const result = await page.evaluate(() => {
      const modeSelect = document.getElementById('remedial-mode-select');
      const onlineLinkInput = document.getElementById('remedial-online-link-input');
      if (!(modeSelect instanceof HTMLSelectElement) || !(onlineLinkInput instanceof HTMLInputElement)) {
        return null;
      }
      onlineLinkInput.value = 'https://meet.example.edu/remedial/cse500';
      modeSelect.value = 'online';
      modeSelect.dispatchEvent(new Event('change', { bubbles: true }));
      return {
        value: onlineLinkInput.value,
        readOnly: onlineLinkInput.readOnly,
      };
    });

    expect(result).not.toBeNull();
    expect(result.value).toBe('https://meet.example.edu/remedial/cse500');
    expect(result.readOnly).toBe(false);
  });
});
