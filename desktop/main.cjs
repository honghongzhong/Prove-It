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
    fs.writeFileSync(smoke, JSON.stringify({ packaged: app.isPackaged, origin, status: response.status, proofs }, null, 2));
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
