const { app, BrowserWindow, dialog, shell, Menu } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
app.setName('ProveIt');
let backend, window, quitting = false;
const smoke = process.env.PROVEIT_SMOKE_REPORT;
if (process.env.PROVEIT_DESKTOP_DATA_DIR) app.setPath('userData', path.resolve(process.env.PROVEIT_DESKTOP_DATA_DIR));
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.focus(); } });
  app.whenReady().then(start).catch(error => { dialog.showErrorBox('ProveIt', error.message); app.quit(); });
}
async function start() {
  const data = app.getPath('userData');
  fs.mkdirSync(data, { recursive: true });
  // Optional local configuration: never shipped or committed, no shell evaluation.
  const configPath = path.join(data, 'toolchain.json');
  const config = fs.existsSync(configPath) ? JSON.parse(fs.readFileSync(configPath, 'utf8')) : {};
  const env = { ...process.env, PROVEIT_DATA_DIR: path.join(data, 'workspace'), PYTHONUTF8: '1' };
  for (const key of ['LEAN_EXE', 'LAKE_EXE', 'CODEX_EXE']) if (typeof config[key] === 'string') env[key] = config[key];
  const pathKey = Object.keys(env).find(k => k.toLowerCase() === 'path') || 'PATH';
  env[pathKey] = [path.join(os.homedir(), '.elan', 'bin'), path.join(os.homedir(), '.cargo', 'bin'), path.join(process.env.APPDATA || data, 'npm'), env[pathKey] || ''].join(path.delimiter);
  const exe = app.isPackaged ? path.join(process.resourcesPath, 'backend', 'proveit-backend.exe') : (process.env.PYTHON_EXE || 'python');
  const args = app.isPackaged ? [] : [path.join(__dirname, 'backend.py')];
  backend = spawn(exe, args, { env, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  let errors = '', line = '';
  backend.stderr.on('data', data => { errors = (errors + data.toString()).slice(-4000); });
  const port = await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Backend startup timed out. Check toolchain.json and restart.')), 30000);
    backend.once('error', error => { clearTimeout(timeout); reject(error); });
    backend.once('exit', code => { clearTimeout(timeout); reject(new Error(`Backend exited (${code}). ${errors}`)); });
    backend.stdout.on('data', data => {
      line += data.toString();
      let newline;
      while ((newline = line.indexOf('\n')) >= 0) {
        const value = line.slice(0, newline); line = line.slice(newline + 1);
        try { const event = JSON.parse(value); if (event.ready && Number.isInteger(event.port)) { clearTimeout(timeout); resolve(event.port); } } catch {}
      }
    });
  });
  const origin = `http://127.0.0.1:${port}`;
  window = new BrowserWindow({ width: 1280, height: 850, minWidth: 720, minHeight: 540, icon: path.join(__dirname, 'icon.png'), show: false, backgroundColor: '#111113', autoHideMenuBar: true, webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true } });
  window.webContents.session.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  function external(url) { try { if (['https:', 'http:'].includes(new URL(url).protocol)) shell.openExternal(url); } catch {} }
  window.webContents.setWindowOpenHandler(({ url }) => { external(url); return { action: 'deny' }; });
  window.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== origin) { event.preventDefault(); external(url); } });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: 'ProveIt', submenu: [{ label: 'Open data folder / 打开数据目录', click: () => shell.openPath(data) }, { label: 'Setup guide / 安装说明', click: () => shell.openExternal('https://github.com/honghongzhong/Prove-It/blob/main/docs/INSTALL.md') }, { type: 'separator' }, { role: 'quit' }] },
    { role: 'editMenu' }, { role: 'viewMenu' }
  ]));
  backend.on('exit', code => { if (!quitting) { dialog.showErrorBox('ProveIt', `Backend stopped (${code}). Restart the app. Your saved research is retained.`); app.quit(); } });
  await window.loadURL(origin);
  if (!smoke) window.show();
  if (smoke) {
    // Release smoke hook: exercises the installed renderer and backend in an isolated data directory.
    const response = await fetch(`${origin}/api/proofs`);
    const proofs = await response.json();
    const renderer = await window.webContents.executeJavaScript(`(async () => {
      for (let i=0;i<200;i++) {
        if (document.querySelector('#dialog').open || document.querySelector('#connection-status').textContent.includes('ready')) break;
        await new Promise(r=>setTimeout(r,100));
      }
      const dialog = document.querySelector('#dialog');
      const report = { onboarding: dialog.open, title: dialog.querySelector('h2')?.textContent, errors: [] };
      if (dialog.open) {
        const provider = dialog.querySelector('[name=provider]');
        provider.value='api'; provider.dispatchEvent(new Event('change'));
        report.apiFieldsVisible = !document.querySelector('#api-settings').hidden;
        report.keyIsPassword = dialog.querySelector('[name=apiKey]').type === 'password';
        report.codexFieldsHidden = document.querySelector('#codex-settings').hidden;
        provider.value='codex'; provider.dispatchEvent(new Event('change'));
        report.guideVisible = !document.querySelector('#codex-settings').hidden;
      }
      report.horizontalOverflow = document.documentElement.scrollWidth > innerWidth;
      return report;
    })()`);
    if (process.env.PROVEIT_SMOKE_API && renderer.onboarding) {
      const http = require('node:http');
      const endpoint = http.createServer((req, res) => {
        req.resume();
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({choices: [{message: {role: 'assistant', content: 'OK'}}]}));
      });
      await new Promise(resolve => endpoint.listen(0, '127.0.0.1', resolve));
      try {
        renderer.apiSaveAndTest = await window.webContents.executeJavaScript(`(async () => {
          const dialog = document.querySelector('#dialog');
          const select = dialog.querySelector('[name=provider]');
          select.value='api'; select.dispatchEvent(new Event('change'));
          dialog.querySelector('[name=baseUrl]').value='http://127.0.0.1:${endpoint.address().port}/v1';
          dialog.querySelector('[name=apiModel]').value='qa-model';
          dialog.querySelector('[name=apiKey]').value='fake-local-key';
          document.querySelector('#test-connection').click();
          for (let i=0;i<200 && document.querySelector('#test-connection').disabled;i++) await new Promise(r=>setTimeout(r,100));
          const settings = await (await fetch('/api/settings')).json();
          const connection = await (await fetch('/api/connection')).json();
          return { result: document.querySelector('#connection-result').textContent, keyFieldCleared: dialog.querySelector('[name=apiKey]').value === '', settingsRedacted: !('apiKey' in settings.settings), keyConfigured: connection.keyConfigured, provider: settings.settings.provider, model: settings.settings.apiModel };
        })()`);
      } finally { endpoint.close(); }
    }
    if (process.env.PROVEIT_SMOKE_ENV) {
      renderer.environmentSetup = await window.webContents.executeJavaScript(`(async () => {
        document.querySelector('#dialog').close();
        await document.querySelector('#environments').onclick();
        const panel = document.querySelector('#dialog');
        const presets = panel.querySelectorAll('[data-setup-env]').length;
        panel.querySelector('[data-setup-env="core"]').click();
        let job;
        for (let i=0;i<300;i++) {
          await new Promise(r=>setTimeout(r,100));
          const data = await (await fetch('/api/lean/environments/jobs')).json();
          job = data.jobs.filter(j=>j.preset === 'core').at(-1);
          if (job && !['queued','running'].includes(job.status)) { await new Promise(r=>setTimeout(r,1700)); break; }
        }
        return {presets, coreSetupStatus:job?.status, smokeVerified:job?.result?.smokeVerified, panelOpen:panel.open, horizontalOverflow:document.documentElement.scrollWidth > innerWidth};
      })()`);
    }
    fs.writeFileSync(smoke, JSON.stringify({ packaged: app.isPackaged, origin, status: response.status, proofs, renderer }, null, 2));
    window.showInactive();
    await window.webContents.executeJavaScript("document.fonts.ready");
    await new Promise(resolve => setTimeout(resolve, 700));
    const screenshot = await window.webContents.capturePage();
    fs.writeFileSync(smoke + '.png', screenshot.toPNG());
    setTimeout(() => app.quit(), 1000);
  }
}
app.on('window-all-closed', () => app.quit());
app.on('before-quit', event => {
  if (!quitting && backend && backend.exitCode === null) {
    event.preventDefault(); quitting = true;
    backend.once('exit', () => app.quit());
    backend.stdin.end();
    setTimeout(() => { if (backend.exitCode === null) backend.kill(); app.quit(); }, 10000).unref();
  }
});
