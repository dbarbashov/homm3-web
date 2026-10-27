export class Engine {
  static async create() {
    const response = await fetch('./engine.wasm');
    if (!response.ok) throw new Error('Сначала выполните npm run build');
    const { instance } = await WebAssembly.instantiate(await response.arrayBuffer());
    return new Engine(instance.exports);
  }
  constructor(exports) { this.exports = exports; }
  input(buffer) {
    const data = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    const ptr = this.exports.input_buffer(data.length);
    if (!ptr) throw new Error('Слишком большой файл');
    new Uint8Array(this.exports.memory.buffer, ptr, data.length).set(data);
  }
  result(status) {
    const bytes = new Uint8Array(this.exports.memory.buffer, this.exports.output_ptr(), this.exports.output_len());
    if (!status) throw new Error(new TextDecoder().decode(bytes));
    return bytes;
  }
  json(status) { return JSON.parse(new TextDecoder().decode(this.result(status))); }
  map(buffer) { this.input(buffer); return this.json(this.exports.parse_map()); }
  sprite(buffer, { opaque = false, animated = false } = {}) {
    this.input(buffer);
    const info = this.json(this.exports.sprite_info());
    const frames = [];
    // Decode all terrain tiles, first adventure-animation group, with a modest cap.
    const groupIndex = 0;
    const count = info.kind === 69 || animated ? Math.min(info.groups[groupIndex].count, 512) : 1;
    for (let i = 0; i < count; i++) {
      const bytes = this.result(this.exports.sprite_frame(groupIndex, i, opaque ? 1 : 0));
      const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
      const [width, height, cw, ch, x, y] = Array.from({ length: 6 }, (_, n) => view.getInt32(n * 4, true));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, cw); canvas.height = Math.max(1, ch);
      if (cw && ch) canvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(bytes.slice(24)), cw, ch), 0, 0);
      frames.push({ canvas, width, height, x, y });
    }
    return { ...info, frames };
  }
}
