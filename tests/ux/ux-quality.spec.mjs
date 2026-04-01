import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('UX Quality Gates', () => {
  test('initial shell boots without uncaught runtime errors', async ({ page }) => {
    const pageErrors = [];
    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
    });

    await page.goto('/web/');
    await page.waitForLoadState('networkidle');

    expect(pageErrors).toEqual([]);
  });

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

  test('admin profile rectification submodule exposes search and edit controls', async ({ page }) => {
    await page.goto('/web/');
    await page.waitForLoadState('networkidle');

    const result = await page.evaluate(() => {
      if (
        typeof authState === 'undefined'
        || typeof state === 'undefined'
        || typeof applyRoleUI !== 'function'
        || typeof setAdminSubmodule !== 'function'
      ) {
        return null;
      }

      authState.user = {
        id: 1,
        email: 'admin@example.com',
        role: 'admin',
      };
      state.ui.activeModule = 'attendance';

      applyRoleUI();
      document.getElementById('admin-profile-rectification-card')?.classList.add('hidden');
      setAdminSubmodule('attendance', 'attendance-rectification');

      const card = document.getElementById('admin-profile-rectification-card');
      const searchBtn = document.getElementById('admin-profile-rectification-search-btn');
      const saveBtn = document.getElementById('admin-profile-rectification-save-btn');
      const picker = document.getElementById('admin-attendance-submodule-select');
      const queryInput = document.getElementById('admin-profile-rectification-query');

      if (
        !(card instanceof HTMLElement)
        || !(searchBtn instanceof HTMLButtonElement)
        || !(saveBtn instanceof HTMLButtonElement)
        || !(picker instanceof HTMLSelectElement)
        || !(queryInput instanceof HTMLInputElement)
      ) {
        return null;
      }

      return {
        display: window.getComputedStyle(card).display,
        hiddenClass: card.classList.contains('hidden'),
        activeClass: card.classList.contains('is-active'),
        pickerValue: picker.value,
        searchLabel: String(searchBtn.textContent || '').trim(),
        saveLabel: String(saveBtn.textContent || '').trim(),
        queryPlaceholder: queryInput.placeholder,
      };
    });

    expect(result).not.toBeNull();
    expect(result.display).not.toBe('none');
    expect(result.hiddenClass).toBe(false);
    expect(result.activeClass).toBe(true);
    expect(result.pickerValue).toBe('attendance-rectification');
    expect(result.searchLabel).toBe('Search Profile');
    expect(result.saveLabel).toBe('Apply Rectification');
    expect(result.queryPlaceholder).toContain('22BCS101');
  });

  test('faculty sidebar messages button opens received-messages popup', async ({ page }) => {
    await page.goto('/web/');
    await page.waitForLoadState('networkidle');

    const result = await page.evaluate(async () => {
      if (
        typeof authState === 'undefined'
        || typeof state === 'undefined'
        || typeof applyRoleUI !== 'function'
        || typeof renderSupportDeskWidget !== 'function'
      ) {
        return null;
      }

      authState.user = {
        id: 2,
        email: 'faculty@example.com',
        role: 'faculty',
        faculty_id: 11,
      };
      state.ui.activeModule = 'attendance';
      state.supportDesk.contacts = [{ id: 101, name: 'Student One', section: 'P132', descriptor: 'P132' }];
      state.supportDesk.threads = [{
        counterparty_id: 101,
        counterparty_name: 'Student One',
        section: 'P132',
        category: 'Attendance',
        subject: 'Attendance Query',
        last_message: 'Please review my attendance.',
        last_sender_role: 'student',
        last_created_at: new Date().toISOString(),
        unread_count: 2,
      }];
      state.supportDesk.messages = [{
        id: 1,
        student_id: 101,
        faculty_id: 11,
        section: 'P132',
        category: 'Attendance',
        subject: 'Attendance Query',
        message: 'Please review my attendance.',
        sender_role: 'student',
        created_at: new Date().toISOString(),
      }];
      state.supportDesk.selectedCounterpartyId = 101;
      state.supportDesk.selectedCategory = 'Attendance';
      state.supportDesk.unreadTotal = 2;

      refreshSupportDeskContext = async () => {
        renderSupportDeskWidget();
      };

      applyRoleUI();

      const button = document.getElementById('nav-messages-btn');
      if (!(button instanceof HTMLButtonElement)) {
        return null;
      }
      button.click();
      await new Promise((resolve) => window.setTimeout(resolve, 0));

      const panel = document.getElementById('support-desk-panel');
      const status = document.getElementById('support-desk-status');
      const unread = document.getElementById('nav-messages-unread-badge');

      if (!(panel instanceof HTMLElement) || !(status instanceof HTMLElement) || !(unread instanceof HTMLElement)) {
        return null;
      }

      return {
        buttonHidden: button.classList.contains('hidden'),
        buttonActive: button.classList.contains('active'),
        unreadText: unread.textContent?.trim() || '',
        panelDisplay: window.getComputedStyle(panel).display,
        widgetOpen: document.getElementById('support-desk-widget')?.classList.contains('is-open') || false,
        statusText: status.textContent?.trim() || '',
        panelText: panel.innerText.slice(0, 220),
      };
    });

    expect(result).not.toBeNull();
    expect(result.buttonHidden).toBe(false);
    expect(result.buttonActive).toBe(true);
    expect(result.unreadText).toBe('2');
    expect(result.widgetOpen).toBe(true);
    expect(result.panelDisplay).not.toBe('none');
    expect(result.statusText).toContain('Received student messages loaded');
    expect(result.panelText).toContain('Faculty Messages');
    expect(result.panelText).toContain('Student One');
  });
});
