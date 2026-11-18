import { chromium } from 'playwright';

async function testLoginPage() {
  console.log('Iniciando verificación de la Pantalla de Login Completa (LoginPage)...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  // Asegurar que no haya sesión previa
  await page.addInitScript(() => {
    localStorage.removeItem('caso16_authenticated');
  });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  console.log('Página cargada.');

  // 1. Verificar Pantalla de Login Completa
  const loginHeadline = page.locator('.login-headline');
  const hasHeadline = await loginHeadline.count() > 0;
  console.log('Pantalla de Login Completa visible:', hasHeadline ? 'SÍ' : 'NO');
  if (hasHeadline) {
    console.log('  Titular detectado:', (await loginHeadline.textContent()).trim());
  }

  // Capturar pantalla de Login
  await page.screenshot({ path: 'screenshot_full_login_page.png', fullPage: false });
  console.log('Captura guardada: screenshot_full_login_page.png');

  // 2. Probar acceso rápido con preset "Superadministrador"
  console.log('Haciendo clic en preset de acceso rápido: Superadministrador...');
  const adminPresetBtn = page.locator('.login-preset-card:has-text("Alejandro Morales")');
  await adminPresetBtn.click();
  await page.waitForTimeout(600);

  // 3. Verificar que ingresó al Command Center
  const securityOverviewTitle = page.locator('h1.page-title:has-text("Security Overview")');
  const inDashboard = await securityOverviewTitle.count() > 0;
  console.log('Acceso al Command Center exitoso:', inDashboard ? 'SÍ' : 'NO');

  // Capturar pantalla del Command Center autenticado
  await page.screenshot({ path: 'screenshot_command_center_authenticated.png', fullPage: false });
  console.log('Captura guardada: screenshot_command_center_authenticated.png');

  // 4. Probar "Cerrar Sesión" para volver a la pantalla de login grande
  console.log('Probando botón "Cerrar Sesión" en el header...');
  const logoutBtn = page.locator('button:has-text("Cerrar Sesión")').first();
  await logoutBtn.click();
  await page.waitForTimeout(500);

  const backToLogin = await page.locator('.login-headline').count() > 0;
  console.log('Retorno a Pantalla de Login exitoso:', backToLogin ? 'SÍ' : 'NO');

  await browser.close();
  console.log('Prueba de Pantalla de Login completada satisfactoriamente.');
}

testLoginPage().catch(err => {
  console.error('Error en prueba de login:', err);
  process.exit(1);
});
