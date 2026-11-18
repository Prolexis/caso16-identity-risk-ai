import { chromium } from 'playwright';

async function check() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  
  // Test 1366x768 Dark Mode
  const pageDark = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  await pageDark.addInitScript(() => localStorage.removeItem('caso16_authenticated'));
  await pageDark.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await pageDark.screenshot({ path: 'frontend/screenshot_login_1366x768_dark.png' });

  // Test 1366x768 Light Mode
  const themeBtn = pageDark.locator('button[aria-label*="Alternar tema"]').first();
  await themeBtn.click();
  await pageDark.waitForTimeout(400);
  await pageDark.screenshot({ path: 'frontend/screenshot_login_1366x768_light.png' });

  // Verify responsive 1-click login
  const socPreset = pageDark.locator('.login-preset-card:has-text("Valeria Quispe")');
  await socPreset.click();
  await pageDark.waitForTimeout(600);
  await pageDark.screenshot({ path: 'frontend/screenshot_command_center_1366x768_light.png' });

  await browser.close();
  console.log('All screenshots captured successfully.');
}

check().catch(console.error);
