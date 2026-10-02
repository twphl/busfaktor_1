// Plays complete games of spielen.html in Chromium, once alone against bots
// and once with two people on one device, and checks that the table can be
// operated by clicking alone: every decision must be reachable, the handover
// must hide the hand, and the game must reach its result.
//
//   node website/tests/check_game_ui.mjs
//
// PLAYWRIGHT_MODULE and CHROMIUM_PATH override where Playwright and the
// browser are found.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const website = path.resolve(here, '..');
const playwrightModule = process.env.PLAYWRIGHT_MODULE || 'playwright';
const playwright = await import(playwrightModule.startsWith('/') ? pathToFileURL(playwrightModule).href : playwrightModule);
// Playwright is CommonJS: loaded by path, its exports sit on `default`.
const { chromium } = playwright.chromium ? playwright : playwright.default;

const types = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.ttf': 'font/ttf', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.png': 'image/png',
};
const server = http.createServer((request, response) => {
  const file = path.join(website, decodeURIComponent(new URL(request.url, 'http://x').pathname));
  if (!file.startsWith(website) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    response.writeHead(404).end();
    return;
  }
  response.writeHead(200, { 'content-type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(response);
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;

const problems = [];
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--no-sandbox'] });

async function openTable(mode, seats) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  page.on('pageerror', (error) => problems.push(`Seitenfehler: ${error.message}`));
  page.on('console', (message) => { if (message.type() === 'error') problems.push(`Konsole: ${message.text()}`); });
  await page.goto(`${base}/spielen.html`);
  await page.click(`.mode-switch [data-mode="${mode}"]`);
  const rows = await page.locator('.seat-row').count();
  for (let index = rows; index < seats.length; index += 1) await page.click('#add-seat');
  for (const [index, role] of seats.entries()) await page.locator('.seat-row .seat-role').nth(index).selectOption(role);
  await page.click('#start-game');
  // With several people the handover covers the bar right away, so the bar's
  // own controls are only reachable in the solo table.
  if (seats.filter((role) => role === 'human').length === 1) await page.check('#fast-bots');
  return page;
}

/** Clicks the first decision offered in the side panel. */
async function act(page) {
  const handover = page.locator('#handover-go');
  if (await handover.isVisible()) {
    const hand = await page.locator('#hand .gc').count();
    if (hand > 0) problems.push('Übergabe: die Hand der nächsten Person ist sichtbar');
    await handover.click();
    return true;
  }
  // Prefer playing a card, so the run exercises more than ending turns.
  const card = page.locator('#hand .gc.is-playable').first();
  if (await card.count()) {
    await card.click();
    const offer = page.locator('#prompt .prompt-selection .move').first();
    if (await offer.count()) {
      await offer.click();
      return true;
    }
    await page.keyboard.press('Escape');
  }
  // Everything else comes from the side panel; [data-toggle] only folds a list open.
  const move = page.locator('#prompt .move:not([data-toggle])').first();
  if (await move.count() && await move.isEnabled()) {
    await move.click();
    return true;
  }
  return false;
}

async function playToTheEnd(page, label) {
  const started = Date.now();
  let idle = 0;
  while (!(await page.locator('#result').isVisible())) {
    if (Date.now() - started > 120000) {
      problems.push(`${label}: Zeitüberschreitung in Runde ${await page.textContent('#round')}`);
      return;
    }
    if (await act(page)) {
      idle = 0;
    } else {
      idle += 1;
      if (idle > 60) {
        problems.push(`${label}: keine anklickbare Entscheidung mehr (${(await page.textContent('#prompt')).slice(0, 120)})`);
        return;
      }
      await page.waitForTimeout(100);
    }
  }
  const title = await page.textContent('#result-title');
  if (!/Sieg/.test(title)) problems.push(`${label}: unerwartetes Ergebnis „${title}“`);
  const rows = await page.locator('#result-rows tr').count();
  if (rows < 2) problems.push(`${label}: Ergebnistabelle hat ${rows} Zeilen`);
  console.log(`${label}: ${title}, Runde ${await page.textContent('#round')}, ${rows} Personen gewertet`);
}

// 1. One person against two bots.
const solo = await openTable('solo', ['human', 'umsichtig', 'kooperativ']);
await playToTheEnd(solo, 'Allein gegen Bots');

// 2. Two people on one device: the handover has to hide the hand.
const table = await openTable('table', ['human', 'human']);
await playToTheEnd(table, 'Zwei an einem Gerät');

// 3. A running game survives a reload.
const resume = await openTable('solo', ['human', 'umsichtig']);
for (let step = 0; step < 12; step += 1) await act(resume);
const roundBefore = await resume.textContent('#round');
await resume.reload();
if (!(await resume.locator('#resume').isVisible())) {
  problems.push('Fortsetzen: keine laufende Partie angeboten');
} else {
  await resume.click('#resume-game');
  await resume.waitForSelector('#play:not([hidden])');
  const roundAfter = await resume.textContent('#round');
  if (roundBefore !== roundAfter) problems.push(`Fortsetzen: Runde ${roundBefore} wurde zu ${roundAfter}`);
  console.log(`Fortsetzen: Partie in Runde ${roundAfter} wiederhergestellt`);
}

await browser.close();
server.close();

if (problems.length) {
  console.error(`\n${problems.length} Problem(e):`);
  for (const problem of problems) console.error(`  - ${problem}`);
  process.exit(1);
}
console.log('\nSpieltisch bedienbar: alle Partien durchgespielt, keine Seitenfehler.');
