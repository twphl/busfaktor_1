// Renders every canonical card with website/renderer.js in Chromium and
// compares the SVG tree with scripts/render_cards.py. Exit code 1 on any
// difference beyond float formatting.
//
//   node website/tests/check_renderer_parity.mjs
//
// PLAYWRIGHT_MODULE and CHROMIUM_PATH override where Playwright and the
// browser are found, DHK_PYTHON the Python command (default python3).
import { spawnSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const website = path.resolve(here, '..');
const playwrightModule = process.env.PLAYWRIGHT_MODULE || 'playwright';
const { chromium } = await import(playwrightModule.startsWith('/') ? pathToFileURL(playwrightModule).href : playwrightModule);

const [pythonCommand, ...pythonArgs] = (process.env.DHK_PYTHON || 'python3').split(' ');
const python = spawnSync(pythonCommand, [...pythonArgs, path.join(here, 'python_reference.py')], { maxBuffer: 1 << 28, encoding: 'utf8' });
if (python.status !== 0) {
  console.error(python.stderr);
  process.exit(2);
}
const references = JSON.parse(python.stdout);

const types = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf' };
const server = http.createServer((request, response) => {
  const file = path.join(website, decodeURIComponent(new URL(request.url, 'http://x').pathname));
  if (!file.startsWith(website) || !fs.existsSync(file)) {
    response.writeHead(404).end();
    return;
  }
  response.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(response);
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--no-sandbox'] });
const page = await browser.newPage();
page.on('pageerror', (error) => console.error('Seitenfehler:', error.message));
await page.goto(`http://127.0.0.1:${server.address().port}/tests/parity.html`);
const results = await page.evaluate((refs) => window.runParity(refs), references);
await browser.close();
server.close();

let failures = 0;
let rounding = 0;
let measured = 0;
let maxDeviation = 0;
for (const [id, report] of Object.entries(results)) {
  rounding += report.rounding;
  measured += report.measured;
  maxDeviation = Math.max(maxDeviation, report.maxDeviation);
  const problems = [
    ...(report.error ? [`Fehler: ${report.error}`] : []),
    ...report.structure,
    ...report.text,
    ...report.attributes,
  ];
  if (problems.length) {
    failures += 1;
    console.log(`✗ ${id}`);
    problems.slice(0, 8).forEach((line) => console.log(`    ${line}`));
    if (problems.length > 8) console.log(`    … ${problems.length - 8} weitere`);
  }
}
const total = Object.keys(results).length;
console.log(`${total - failures}/${total} Karten mit identischer Struktur, identischen Textzeilen und Geometrie.`);
console.log(`${rounding} Werte nur in der Zahlenschreibweise verschieden, ${measured} Positionen aus der Textmessung um höchstens ${maxDeviation.toFixed(4)} Einheiten (${(maxDeviation / 10).toFixed(5)} mm).`);
process.exit(failures ? 1 : 0);
