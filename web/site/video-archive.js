/* Original VID directory: uint32 count, then name[40] + uint32 offset. */
export function parseVideoDirectory(bytes, fileSize) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length < 4) throw new Error('Truncated VID header');
  const count = view.getUint32(0, true), end = 4 + count * 44;
  if (count > 10000 || end > bytes.length || end > fileSize) throw new Error('Invalid VID directory');
  const entries = [];
  for (let i = 0; i < count; i++) {
    const at = 4 + i * 44, field = bytes.subarray(at, at + 40), zero = field.indexOf(0);
    if (zero < 1) throw new Error('Invalid VID filename');
    const name = String.fromCharCode(...field.subarray(0, zero));
    const offset = view.getUint32(at + 40, true);
    if (!/^[\w .-]+\.(smk|bik)$/i.test(name) || offset < end || offset >= fileSize) throw new Error('Invalid VID member');
    entries.push({name, offset});
  }
  const ordered = [...entries].sort((a,b)=>a.offset-b.offset);
  for (let i = 0; i < ordered.length; i++) {
    ordered[i].bytes = (ordered[i + 1]?.offset ?? fileSize) - ordered[i].offset;
    if (ordered[i].bytes <= 0 || ordered[i].bytes > 64 * 1024 * 1024) throw new Error('Invalid VID member extent');
  }
  return entries;
}
export async function indexVideoBlob(blob) {
  const header = new DataView(await blob.slice(0, 4).arrayBuffer());
  const count = header.getUint32(0, true);
  if (count > 10000) throw new Error('Invalid VID count');
  return parseVideoDirectory(new Uint8Array(await blob.slice(0, 4 + count * 44).arrayBuffer()), blob.size);
}
