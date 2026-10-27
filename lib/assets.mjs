import { open, readdir } from 'node:fs/promises';
import path from 'node:path';
import { inflateSync } from 'node:zlib';
import { parseVideoDirectory } from '../web/site/video-archive.js';

// LOD directory: 92-byte header, 32-byte members (src/lodfile.cpp).
export function parseLodDirectory(buffer, fileSize = buffer.length) {
  if (buffer.length < 92 || buffer.toString('ascii', 0, 4) !== 'LOD\0') throw new Error('Invalid LOD signature');
  const count = buffer.readUInt32LE(8);
  if (count > 100000 || 92 + count * 32 > buffer.length) throw new Error('Truncated LOD directory');
  const entries = [];
  for (let i = 0; i < count; i++) {
    const at = 92 + i * 32;
    const name = buffer.subarray(at, at + 16).toString('ascii').split('\0')[0];
    const offset = buffer.readUInt32LE(at + 16), size = buffer.readUInt32LE(at + 20), compressed = buffer.readUInt32LE(at + 28);
    if (!name || offset < 92 + count * 32 || offset + (compressed || size) > fileSize || size > 128 * 1024 * 1024) throw new Error(`Invalid LOD entry ${name}`);
    entries.push({ name, offset, size, compressed });
  }
  return entries;
}

export async function openInstallation(root) {
  const entries = new Map(), archives = [], soundArchives = [];
  const data = path.join(root, 'Data');
  const files = await readdir(data);
  // Expansion archives override the base archives, as in the original loader.
  for (const name of ['h3bitmap.lod', 'h3sprite.lod', 'h3ab_bmp.lod', 'h3ab_spr.lod']) {
    const file = files.find(f => f.toLowerCase() === name);
    if (!file) throw new Error(`Missing ${name}`);
    const full = path.join(data, file), handle = await open(full);
    try {
      const stat = await handle.stat(), header = Buffer.alloc(92);
      await handle.read(header, 0, 92, 0);
      const count = header.readUInt32LE(8);
      if (count > 100000) throw new Error('Invalid LOD entry count');
      const dir = Buffer.alloc(92 + count * 32);
      const read = await handle.read(dir, 0, dir.length, 0);
      if (read.bytesRead !== dir.length) throw new Error('Truncated LOD directory');
      const members = parseLodDirectory(dir, stat.size);
      archives.push({ name: file, bytes: stat.size, entries: members.length });
      for (const member of members) entries.set(member.name.toLowerCase(), { ...member, file: full });
    } finally { await handle.close(); }
  }
  for (const wanted of ['heroes3.snd', 'h3ab_ahd.snd']) {
    const name = files.find(n => n.toLowerCase() === wanted);
    if (!name) { if (wanted === 'heroes3.snd') throw new Error('Missing ' + wanted);continue; }
    const handle = await open(path.join(data, name));
    try { soundArchives.push({ name, bytes: (await handle.stat()).size }); } finally { await handle.close(); }
  }
  const videos = new Map();
  for (const wanted of ['heroes3.vid','video.vid','h3ab_ahd.vid']) {
    const name = files.find(n => n.toLowerCase() === wanted);
    if (!name) continue;
    const file = path.join(data, name), handle = await open(file);
    try {
      const size = (await handle.stat()).size, header = Buffer.alloc(4);
      if ((await handle.read(header,0,4,0)).bytesRead !== 4) throw new Error('Truncated VID header');
      const count = header.readUInt32LE(0);
      if (count > 10000) throw new Error('Invalid VID count');
      const directory = Buffer.alloc(4 + count * 44);
      if ((await handle.read(directory,0,directory.length,0)).bytesRead !== directory.length) throw new Error('Truncated VID directory');
      for (const entry of parseVideoDirectory(directory,size)) videos.set(entry.name.toLowerCase(),{...entry,file});
    } finally { await handle.close(); }
  }
  const campaigns = (await readdir(path.join(root,'Maps'))).filter(f => /\.h3c$/i.test(f)).sort();
  const maps = (await readdir(path.join(root, 'Maps'))).filter(f => /\.h3m$/i.test(f)).sort();
  const music = (await readdir(path.join(root, 'Mp3'))).filter(f => /\.mp3$/i.test(f)).sort();
  return { root, maps, campaigns, music, entries, archives, soundArchives, videos };
}

export async function readAsset(installation, name) {
  const entry = installation.entries.get(name.toLowerCase());
  if (!entry) return null;
  const file = await open(entry.file);
  try {
    const stored = Buffer.alloc(entry.compressed || entry.size);
    const read = await file.read(stored, 0, stored.length, entry.offset);
    if (read.bytesRead !== stored.length) throw new Error('Truncated member');
    const data = entry.compressed ? inflateSync(stored, { maxOutputLength: entry.size }) : stored;
    if (data.length !== entry.size) throw new Error('LOD member size mismatch');
    return data;
  } finally { await file.close(); }
}
