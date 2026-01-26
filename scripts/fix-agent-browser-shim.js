const fs = require('fs');
const path = require('path');

function main() {
  if (process.platform !== 'win32') {
    return;
  }

  const root = process.cwd();
  const binDir = path.join(root, 'node_modules', '.bin');
  const pkgDir = path.join(root, 'node_modules', 'agent-browser');
  const exePath = path.join(pkgDir, 'bin', 'agent-browser-win32-x64.exe');

  if (!fs.existsSync(binDir) || !fs.existsSync(exePath)) {
    return;
  }

  const cmdPath = path.join(binDir, 'agent-browser.cmd');
  const ps1Path = path.join(binDir, 'agent-browser.ps1');

  const cmd = [
    '@echo off',
    'setlocal',
    'set "BASEDIR=%~dp0"',
    '"%BASEDIR%..\\agent-browser\\bin\\agent-browser-win32-x64.exe" %*',
    '',
  ].join('\r\n');

  const ps1 = [
    '#!/usr/bin/env pwsh',
    '$basedir=Split-Path $MyInvocation.MyCommand.Definition -Parent',
    '& "$basedir/../agent-browser/bin/agent-browser-win32-x64.exe" @args',
    'exit $LASTEXITCODE',
    '',
  ].join('\n');

  fs.writeFileSync(cmdPath, cmd, 'utf8');
  fs.writeFileSync(ps1Path, ps1, 'utf8');
}

main();
