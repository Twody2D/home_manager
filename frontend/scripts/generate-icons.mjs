// One-off icon generator: draws a simple house glyph on a solid background
// and writes raw PNGs, with no image-library dependency (just Node's zlib).
import { deflateSync } from "node:zlib";
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "..", "public", "icons");
mkdirSync(outDir, { recursive: true });

const BG = [37, 99, 235]; // Tailwind blue-600
const FG = [255, 255, 255];

function crc32(buf) {
  let c;
  const table = crc32.table ?? (crc32.table = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c;
    }
    return t;
  })());
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    crc = table[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const typeBuf = Buffer.from(type, "ascii");
  const lenBuf = Buffer.alloc(4);
  lenBuf.writeUInt32BE(data.length, 0);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([lenBuf, typeBuf, data, crcBuf]);
}

function inTriangle(px, py, ax, ay, bx, by, cx, cy) {
  const d1 = (px - bx) * (ay - by) - (ax - bx) * (py - by);
  const d2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy);
  const d3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay);
  const hasNeg = d1 < 0 || d2 < 0 || d3 < 0;
  const hasPos = d1 > 0 || d2 > 0 || d3 > 0;
  return !(hasNeg && hasPos);
}

function pixelColor(x, y, n) {
  const fx = x / n;
  const fy = y / n;

  const inBody = fx >= 0.28 && fx <= 0.72 && fy >= 0.52 && fy <= 0.82;
  const inRoof = inTriangle(fx, fy, 0.5, 0.2, 0.2, 0.52, 0.8, 0.52);
  const inDoor = fx >= 0.45 && fx <= 0.55 && fy >= 0.66 && fy <= 0.82;

  if ((inBody && !inDoor) || inRoof) return FG;
  return BG;
}

function writePng(n, filePath) {
  const raw = Buffer.alloc(n * (1 + n * 3));
  for (let y = 0; y < n; y++) {
    const rowStart = y * (1 + n * 3);
    raw[rowStart] = 0; // filter: none
    for (let x = 0; x < n; x++) {
      const [r, g, b] = pixelColor(x, y, n);
      const px = rowStart + 1 + x * 3;
      raw[px] = r;
      raw[px + 1] = g;
      raw[px + 2] = b;
    }
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(n, 0);
  ihdr.writeUInt32BE(n, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // color type: RGB
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  const png = Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);

  writeFileSync(filePath, png);
  console.log(`wrote ${filePath} (${n}x${n})`);
}

for (const size of [180, 192, 512]) {
  writePng(size, path.join(outDir, `icon-${size}.png`));
}
