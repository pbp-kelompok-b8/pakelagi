const { test, expect } = require('@playwright/test');

for (const action of ['click', 'wheel', 'Escape', 'button']) {
  test(`user can skip using ${action} and access the login form`, async ({ page }) => {
    await page.goto('/accounts/login/');
    const intro = page.getByRole('dialog', { name: 'Intro Pakelagi' });
    await expect(intro).toBeVisible();
    if (action === 'click') await intro.click({ position: { x: 10, y: 100 } });
    if (action === 'wheel') await page.mouse.wheel(0, 100);
    if (action === 'Escape') await page.keyboard.press('Escape');
    if (action === 'button') await page.getByRole('button', { name: 'Lewati intro' }).press('Enter');
    await expect(intro).toBeHidden();
    await page.getByLabel('Username').fill('pengunjung');
  });
}

for (const fallback of ['reduced motion', 'storage failure', 'image failure', 'no javascript']) {
  test(`content stays accessible with ${fallback}`, async ({ browser }) => {
    const context = await browser.newContext({
      reducedMotion: fallback === 'reduced motion' ? 'reduce' : 'no-preference',
      javaScriptEnabled: fallback !== 'no javascript',
    });
    if (fallback === 'storage failure') {
      await context.addInitScript(() => {
        Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('unavailable'); } });
      });
    }
    if (fallback === 'image failure') await context.route('**/static/intro/**', route => route.abort());
    const page = await context.newPage();
    await page.goto('/accounts/login/');
    await expect(page.getByRole('dialog', { name: 'Intro Pakelagi' })).toBeHidden();
    await page.getByLabel('Username').fill('pengunjung');
    await context.close();
  });
}

for (const key of ['Tab', 'Shift+Tab']) {
  test(`leaving the intro with ${key} reveals the focused page`, async ({ page }) => {
    await page.goto('/accounts/login/');
    await expect(page.getByRole('button', { name: 'Lewati intro' })).toBeFocused();
    await page.keyboard.press(key);
    await expect(page.getByRole('dialog', { name: 'Intro Pakelagi' })).toBeHidden();
  });
}

test('skipping restores keyboard focus to the destination page', async ({ page }) => {
  await page.goto('/accounts/login/');
  await page.getByRole('button', { name: 'Lewati intro' }).press('Enter');
  await expect(page.locator('main')).toBeFocused();
});

test('stalled image loading releases the page after five seconds', async ({ page }) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.route('**/static/intro/**', () => {});
  await page.goto('/accounts/login/', { waitUntil: 'domcontentloaded' });
  const intro = page.getByRole('dialog', { name: 'Intro Pakelagi' });
  await expect(intro).toBeHidden();
  await page.getByLabel('Username').fill('pengunjung');
  await page.clock.runFor(5000);
  await expect(intro).toBeHidden();
});

test('mobile intro fits the viewport and can be skipped by touch scroll', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/accounts/login/');
  const intro = page.getByRole('dialog', { name: 'Intro Pakelagi' });
  await expect(intro).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await intro.dispatchEvent('touchmove');
  await expect(intro).toBeHidden();
});

test('first visit shows paired photos then reveals the requested page once per tab', async ({ page }) => {
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  await page.goto('/accounts/login/?next=/');
  const intro = page.getByRole('dialog', { name: 'Intro Pakelagi' });
  await expect(intro).toBeVisible();
  await expect(intro.locator('img:visible')).toHaveCount(2);
  expect(await intro.locator('img').evaluateAll(images => images.length === 16 && images.every(image => image.complete && image.naturalWidth > 0))).toBe(true);
  await expect(intro.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '8');
  for (const progress of [21, 34, 47, 63, 78, 91, 100]) {
    await page.clock.runFor(180);
    await expect(intro.getByRole('progressbar')).toHaveAttribute('aria-valuenow', String(progress));
  }
  await page.clock.runFor(180);
  await expect(intro.getByText('Dipakai lagi, dicintai lagi.')).toBeVisible();
  await page.clock.runFor(1200);
  await expect(intro).toBeHidden();
  await expect(page).toHaveURL(/accounts\/login\/\?next=\/$/);
  await page.reload();
  await expect(intro).toBeHidden();
});
