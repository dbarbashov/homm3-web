import http from 'node:http';
import net from 'node:net';
import { networkInterfaces, hostname } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readFile } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { gunzipSync } from 'node:zlib';
import { openInstallation, readAsset } from './lib/assets.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
let installation = null, setupError = '';
try {
  const config = JSON.parse(await readFile(path.join(root, '.local/game.json'), 'utf8'));
  installation = await openInstallation(config.gameRoot);
} catch (error) { setupError = error.message; console.warn('Local game not configured:', setupError); }
const port = Number(process.env.PORT || 8783);
const bindAddress = process.env.HOST || '0.0.0.0';
const lanAddresses = Object.values(networkInterfaces()).flat().filter(n => n.family === 'IPv4' && !n.internal && /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(n.address)).map(n => n.address);
const allowedHosts = new Set(['127.0.0.1', 'localhost', ...lanAddresses, hostname().toLowerCase()]);
const mime = { '.webp': 'image/webp', '.png': 'image/png', '.ico': 'image/x-icon', '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css', '.wasm': 'application/wasm', '.webmanifest': 'application/manifest+json', '.json': 'application/json' };
const staticFiles = new Set(['site/crest.webp', 'site/ui-leather.webp', 'site/ui-gold.webp', 'favicon.ico', 'site/favicon.png', 'viewer.html', 'site/site.css', 'site/fonts.css', 'site/skin.css', 'site/mobile.css', 'site/mobile.js', 'site/touch.js', 'site/report-bug.js', 'site/game.webmanifest', 'site/assets.js', 'site/video-archive.js', 'site/resources.json', 'site/rooms.js', 'site/status.html', 'site/credits.html', 'index.html', 'app.js', 'engine.js', 'renderer.js', 'style.css', 'engine.wasm', 'status.html', 'port/index.html', 'port/boot.js', 'port/sha256.js', 'port/music.js', 'port/sfx.js', 'port/homm3.js', 'port/homm3.wasm', 'port/status.html', 'port/game.html', 'port/game.js', 'port/game.wasm']);

const server = http.createServer(async (req, res) => {
  const send = (status, body, type = 'application/octet-stream') => {
    res.writeHead(status, { 'Content-Type': type, 'Content-Length': Buffer.byteLength(body), 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    res.end(body);
  };
  try {
    if (!allowedHosts.has((req.headers.host || '').split(':')[0].toLowerCase())) return send(403, 'Local network access only');
    if (req.url.startsWith('/lobby/')) {
      const proxy = http.request({host:'127.0.0.1',port:8784,path:req.url,method:req.method,headers:req.headers}, upstream => { res.writeHead(upstream.statusCode,upstream.headers); upstream.pipe(res); });
      proxy.on('error', () => { if (!res.headersSent) send(503,'Lobby server unavailable'); else res.destroy(); });
      req.pipe(proxy); return;
    }
    if (req.method !== 'GET') return send(405, 'GET only');
    const url = new URL(req.url, 'http://127.0.0.1');
    const route = decodeURIComponent(url.pathname);
    if (route === '/api/catalog') return send(200, JSON.stringify({ ready: !!installation, error: setupError, maps: installation?.maps || [], campaigns: installation?.campaigns || [], videos: [...(installation?.videos?.keys() || [])], music: installation?.music || [], archives: installation?.archives || [], soundArchives: installation?.soundArchives || [], resources: installation?.entries.size || 0 }), 'application/json');
    if (route.startsWith('/api/')) {
      if (!installation) return send(503, 'Configure .local/game.json with gameRoot first');
      const name = url.searchParams.get('name');
      if (!name) return send(400, 'Missing name');
      if (route === '/api/archive') {
        const archive = [...installation.archives, ...installation.soundArchives].find(a => a.name.toLowerCase() === name.toLowerCase());
        if (!archive) return send(404, 'Archive not found');
        res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Length': archive.bytes, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
        await pipeline(createReadStream(path.join(installation.root, 'Data', archive.name)), res);
        return;
      }
      if (route === '/api/video') {
        const entry = installation.videos.get(name.toLowerCase());
        if (!entry) return send(404,'Video not found');
        res.writeHead(200, {'Content-Type':'application/octet-stream','Content-Length':entry.bytes,'Cache-Control':'private, max-age=86400','X-Content-Type-Options':'nosniff'});
        await pipeline(createReadStream(entry.file,{start:entry.offset,end:entry.offset+entry.bytes-1}),res); return;
      }
      if (route === '/api/asset') {
        const data = await readAsset(installation, name);
        return data ? send(200, data) : send(404, 'Resource not found');
      }
      if (route === '/api/scenario' && [...installation.maps,...installation.campaigns].includes(name)) {
        const file = path.join(installation.root, 'Maps', name);
        res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Cache-Control': 'no-store' });
        await pipeline(createReadStream(file), res);
        return;
      }
      if (route === '/api/map' && installation.maps.includes(name)) {
        const data = await readFile(path.join(installation.root, 'Maps', name));
        return send(200, gunzipSync(data, { maxOutputLength: 128 * 1024 * 1024 }));
      }
      if (route === '/api/music' && installation.music.includes(name)) return send(200, await readFile(path.join(installation.root, 'Mp3', name)), 'audio/mpeg');
      return send(404, 'Not found');
    }
    const filename = route === '/' ? 'index.html' : ['/port', '/port/'].includes(route) ? 'port/index.html' : route.slice(1);
    if (['site/fonts.css', 'site/skin.css'].includes(filename)) {
      return send(200, await readFile(path.join(root,'web',filename)).catch(()=>Buffer.from('/* Optional original UI assets. */')), 'text/css');
    }
    if (!staticFiles.has(filename)) return send(404, 'Not found');
    send(200, await readFile(path.join(root, 'web', filename)), mime[path.extname(filename)]);
  } catch (error) {
    if (res.headersSent || res.destroyed) { res.destroy(); return; }
    console.error(error);
    send(500, 'Could not read or decode this resource');
  }
});
server.on('upgrade', (req, socket, head) => {
  if (req.url !== '/lobby/socket' || !allowedHosts.has((req.headers.host || '').split(':')[0].toLowerCase())) { socket.destroy(); return; }
  const upstream = net.connect(8784, '127.0.0.1', () => {
    upstream.write(`${req.method} ${req.url} HTTP/1.1\r\n` + Object.entries(req.headers).map(([k,v])=>`${k}: ${v}\r\n`).join('') + '\r\n');
    if (head.length) upstream.write(head); socket.pipe(upstream); upstream.pipe(socket);
  });
  upstream.on('error',()=>socket.destroy()); socket.on('error',()=>upstream.destroy()); socket.on('close',()=>upstream.destroy());
});
server.listen(port, bindAddress, () => {
  console.log(`Heroes III: http://127.0.0.1:${port}/port/game.html`);
  for (const address of lanAddresses) console.log(`LAN: http://${address}:${port}/port/game.html`);
});
