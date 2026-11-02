/* Explicit public shell only: never enumerate the web directory. */
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
export const shellFiles = [
  'index.html', 'favicon.ico',
  ...['game.html','game.js','game.wasm','boot.js','sha256.js','music.js','sfx.js'].map(n=>'port/'+n),
  ...['crest.webp','ui-leather.webp','ui-gold.webp','favicon.png','site.css','mobile.css',
    'fonts.css','skin.css','mobile.js','touch.js','report-bug.js','telemetry.js','privacy.html',
    'game.webmanifest','assets.js','video-archive.js','rooms.js','fast-game.js',
    'authority-game.js','offline.html','offline.css','offline.js',
    'offline-store.js','offline-register.js'].map(n=>'site/'+n)
];
export const optionalShellFiles = new Set(['site/fonts.css','site/skin.css']);
export const optionalCSS = '/* Optional locally generated UI assets. */\n';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export async function buildOfflineWorker(root) {
  const entries = [];
  for (const file of shellFiles) {
    const bytes = await readFile(path.join(root,'web',file)).catch(error=>{
      if (error.code==='ENOENT' && optionalShellFiles.has(file)) return Buffer.from(optionalCSS);
      throw error;
    });
    entries.push({url:'/'+file, hash:hash(bytes), bytes:Buffer.byteLength(bytes)});
  }
  const manifest = {version:hash(JSON.stringify(entries)), entries};
  const template = await readFile(path.join(root,'lib/offline-worker.js'),'utf8');
  return template.replace('/* OFFLINE_MANIFEST */ null',JSON.stringify(manifest));
}
