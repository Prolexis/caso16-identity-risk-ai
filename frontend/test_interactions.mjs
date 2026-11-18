import { chromium } from 'playwright';

async function testInteractions() {
  console.log('Iniciando prueba de interacciones (Notificaciones, Roles, Login)...');
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  console.log('Página cargada en http://localhost:5173/');

  // 1. Probar Notificaciones
  console.log('--- Probando campana de notificaciones ---');
  const notifBtn = page.locator('button[aria-label*="notificaciones"]').first();
  await notifBtn.click();
  await page.waitForTimeout(300);

  const drawerTitle = await page.locator('h3:has-text("Notificaciones de Seguridad")');
  console.log('Drawer de notificaciones abierto:', await drawerTitle.count() > 0 ? 'SÍ' : 'NO');

  // Clic en la primera notificación para navegar
  const firstNotif = page.locator('.drawer-panel .drawer-body > div').first();
  await firstNotif.click();
  await page.waitForTimeout(400);
  console.log('Clic en notificación ejecutado.');

  // 2. Probar Selector de Rol en Header
  console.log('--- Probando conmutador de roles en Header ---');
  const roleSelect = page.locator('select.role-selector');
  await roleSelect.selectOption('Analista de ciberseguridad');
  await page.waitForTimeout(400);

  const userNameInSidebar = await page.locator('.sidebar-footer .user-name').textContent();
  const userRoleInSidebar = await page.locator('.sidebar-footer .user-role').textContent();
  console.log('Sidebar después de cambiar a Analista SOC:');
  console.log('  Nombre:', userNameInSidebar);
  console.log('  Rol:', userRoleInSidebar);

  // 3. Probar Login Modal
  console.log('--- Probando Modal de Login Demo ---');
  const loginBtn = page.locator('button:has-text("Login Demo")').first();
  await loginBtn.click();
  await page.waitForTimeout(300);

  const loginModal = page.locator('h3:has-text("Autenticación & Selección de Rol RBAC")');
  console.log('Modal de Login abierto:', await loginModal.count() > 0 ? 'SÍ' : 'NO');

  // Autocompletar con preset Auditor
  const auditorBtn = page.locator('button:has-text("Carlos Mendoza")').first();
  await auditorBtn.click();
  await page.waitForTimeout(400);

  const userNameAfterAuditor = await page.locator('.sidebar-footer .user-name').textContent();
  const userRoleAfterAuditor = await page.locator('.sidebar-footer .user-role').textContent();
  console.log('Sidebar después de Login como Auditor:');
  console.log('  Nombre:', userNameAfterAuditor);
  console.log('  Rol:', userRoleAfterAuditor);

  // Verificar toast
  const toast = page.locator('.floating-toast');
  if (await toast.count() > 0) {
    console.log('Toast visible con texto:', await toast.textContent());
  }

  // Capturar pantalla final
  await page.screenshot({ path: 'screenshot_interactions_success.png', fullPage: false });
  console.log('Captura guardada: screenshot_interactions_success.png');

  console.log('Errores en consola:', errors.length ? errors : '0 errores');
  await browser.close();
  console.log('Prueba de interacciones finalizada exitosamente.');
}

testInteractions().catch(err => {
  console.error('Error en prueba de interacciones:', err);
  process.exit(1);
});
