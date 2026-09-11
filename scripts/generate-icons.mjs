import sharp from 'sharp';
import { mkdir, readFile } from 'node:fs/promises';

await mkdir('public/icons', { recursive: true });
const mark = await readFile('public/icon.svg');
await Promise.all([
  sharp(mark).resize(192, 192).png().toFile('public/icons/icon-192.png'),
  sharp(mark).resize(512, 512).png().toFile('public/icons/icon-512.png'),
  sharp(mark).resize(180, 180).png().toFile('public/apple-touch-icon.png'),
]);
// A padded mark keeps all foreground detail inside the maskable safe zone.
const inset = await sharp(mark).resize(360, 360).png().toBuffer();
await sharp({ create: { width: 512, height: 512, channels: 4, background: '#244a36' } })
  .composite([{ input: inset, left: 76, top: 76 }])
  .png()
  .toFile('public/icons/icon-maskable-512.png');
console.log('Generated all four installation icons.');
