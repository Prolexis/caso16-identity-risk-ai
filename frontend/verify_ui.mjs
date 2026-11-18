import { chromium } from 'playwright';

async function runAudit() {
  console.log('Iniciando auditoría visual con Playwright...');
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    console.log('Chromium launch failed, trying system Chrome/msedge...', err.message);
    try {
      browser = await chromium.launch({ channel: 'msedge', headless: true });
    } catch (e) {
      browser = await chromium.launch({ channel: 'chrome', headless: true });
    }
  }

  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  // Listen for console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  console.log('Página cargada correctamente en http://localhost:5173/');

  // 1. Auditar en Dark Mode (default)
  const darkTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  console.log(`Tema actual detectado: ${darkTheme}`);

  const darkHeroStyles = await page.evaluate(() => {
    const hero = document.querySelector('.page-hero-banner');
    const title = document.querySelector('.page-hero-banner .page-title');
    const desc = document.querySelector('.page-hero-banner .page-desc');
    return {
      heroBg: window.getComputedStyle(hero).backgroundColor,
      titleColor: window.getComputedStyle(title).color,
      descColor: window.getComputedStyle(desc).color,
    };
  });
  console.log('DARK MODE HERO:', darkHeroStyles);

  await page.screenshot({ path: 'screenshot_dark_mode.png', fullPage: false });
  console.log('Captura Dark Mode guardada: screenshot_dark_mode.png');

  // 2. Alternar a Light Mode
  const toggleBtn = await page.locator('button[title*="Modo Claro"]');
  if (await toggleBtn.count() > 0) {
    await toggleBtn.first().click();
  } else {
    // click by aria-label
    await page.locator('button[aria-label*="Alternar tema"]').click();
  }

  await page.waitForTimeout(300);

  const lightTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  console.log(`Tema después de toggle: ${lightTheme}`);

  const lightHeroStyles = await page.evaluate(() => {
    const hero = document.querySelector('.page-hero-banner');
    const title = document.querySelector('.page-hero-banner .page-title');
    const desc = document.querySelector('.page-hero-banner .page-desc');
    const kpiCard = document.querySelector('.kpi-card-enterprise');
    const kpiVal = document.querySelector('.kpi-card-enterprise .kpi-card-value');
    return {
      heroBg: window.getComputedStyle(hero).backgroundColor,
      titleColor: window.getComputedStyle(title).color,
      descColor: window.getComputedStyle(desc).color,
      kpiBg: window.getComputedStyle(kpiCard).backgroundColor,
      kpiValColor: window.getComputedStyle(kpiVal).color,
    };
  });
  console.log('LIGHT MODE HERO & KPI:', lightHeroStyles);

  await page.screenshot({ path: 'screenshot_light_mode.png', fullPage: false });
  console.log('Captura Light Mode guardada: screenshot_light_mode.png');

  // 3. Probar navegación a AI Training Center
  const aiNav = await page.locator('button:has-text("AI Training Center")').first();
  await aiNav.click();
  await page.waitForTimeout(400);

  const aiHeroStyles = await page.evaluate(() => {
    const hero = document.querySelector('.page-hero-banner');
    const title = document.querySelector('.page-hero-banner .page-title');
    return {
      heroBg: window.getComputedStyle(hero).backgroundColor,
      titleColor: window.getComputedStyle(title).color,
    };
  });
  console.log('AI TRAINING CENTER IN LIGHT MODE:', aiHeroStyles);
  await page.screenshot({ path: 'screenshot_ai_training_light.png', fullPage: false });

  console.log('Console errors durante la prueba:', consoleErrors.length ? consoleErrors : 'Ninguno');

  await browser.close();
  console.log('Auditoría visual completada con éxito.');
}

runAudit().catch(err => {
  console.error('Error durante la auditoría:', err);
  process.exit(1);
});
