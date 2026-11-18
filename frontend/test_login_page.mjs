import { chromium } from 'playwright';

async function testLoginPageVisual() {
  console.log('Iniciando verificación visual de la Pantalla de Login con Imagen y Gráfico...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 950 } });
  const page = await context.newPage();

  // Asegurar que no haya sesión previa
  await page.addInitScript(() => {
    localStorage.removeItem('caso16_authenticated');
  });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  console.log('Página cargada.');

  // 1. Captura en Modo Oscuro (predeterminado de ciberseguridad)
  const heroImg = page.locator('img.login-hero-img');
  console.log('Imagen hero presente:', await heroImg.count() > 0 ? 'SÍ' : 'NO');

  const cyberVisual = page.locator('.cyber-visual-wrapper');
  console.log('Topología visual interactiva presente:', await cyberVisual.count() > 0 ? 'SÍ' : 'NO');

  await page.screenshot({ path: 'screenshot_login_pro_dark.png', fullPage: false });
  console.log('Captura Modo Oscuro guardada: screenshot_login_pro_dark.png');

  // 2. Alternar a Modo Claro
  const themeBtn = page.locator('button[aria-label*="Alternar tema"]').first();
  await themeBtn.click();
  await page.waitForTimeout(400);

  await page.screenshot({ path: 'screenshot_login_pro_light.png', fullPage: false });
  console.log('Captura Modo Claro guardada: screenshot_login_pro_light.png');

  // 3. Probar autocompletado y acceso inmediato con 1 clic
  console.log('Probando acceso con 1 clic en preset Analista SOC...');
  const socPreset = page.locator('.login-preset-card:has-text("Valeria Quispe")');
  await socPreset.click();
  await page.waitForTimeout(600);

  const securityOverview = page.locator('h1.page-title:has-text("Security Overview")');
  console.log('Ingreso al Command Center exitoso:', await securityOverview.count() > 0 ? 'SÍ' : 'NO');

  await browser.close();
  console.log('Auditoría visual completada con éxito.');
}

testLoginPageVisual().catch(err => {
  console.error('Error en prueba visual:', err);
  process.exit(1);
});
