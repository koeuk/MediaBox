// TikTok bulk-unliker — personal utility for YOUR OWN account only.
//
// How it works:
//   1. Opens a real (headful) Chromium with a persistent profile in ./session.
//      First run: log in to TikTok manually in that window, then press Enter
//      in this terminal. The session is saved for later runs.
//   2. Opens your profile's "Liked" tab and collects video links.
//   3. Visits each video and clicks the like button to unlike it, slowly,
//      with random human-ish delays. Stops on captcha or after MAX_PER_RUN.
//
// Caveats: automated interaction is against TikTok's ToS — expect captchas or
// temporary action-blocks if you push it. Keep MAX_PER_RUN modest and delays
// long. TikTok's DOM changes often; the data-e2e selectors below may need
// updating when it does.

import {chromium} from 'playwright';
import readline from 'node:readline/promises';
import {stdin, stdout} from 'node:process';

// ── config ──────────────────────────────────────────────────────────────
const PROFILE_URL = process.env.TIKTOK_PROFILE ?? 'https://www.tiktok.com/@koeuk1';
const MAX_PER_RUN = Number(process.env.MAX_PER_RUN ?? 50);
const DELAY_MIN_S = 8; // seconds between unlikes (min)
const DELAY_MAX_S = 18; // seconds between unlikes (max)
// ────────────────────────────────────────────────────────────────────────

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const humanDelay = () =>
  sleep((DELAY_MIN_S + Math.random() * (DELAY_MAX_S - DELAY_MIN_S)) * 1000);

if (!PROFILE_URL) {
  console.error('Set your profile first, e.g.:');
  console.error('  TIKTOK_PROFILE=https://www.tiktok.com/@yourname npm start');
  process.exit(1);
}

const rl = readline.createInterface({input: stdin, output: stdout});

const browser = await chromium.launchPersistentContext('./session', {
  headless: false,
  viewport: {width: 1280, height: 850},
});
const page = browser.pages()[0] ?? (await browser.newPage());

// ── 1. ensure logged in ─────────────────────────────────────────────────
await page.goto('https://www.tiktok.com/', {waitUntil: 'domcontentloaded'});
await sleep(3000);

const loggedIn = async () =>
  (await page.locator('[data-e2e="profile-icon"]').count()) > 0;

if (!(await loggedIn())) {
  console.log('\nNot logged in. Log in to TikTok in the browser window,');
  await rl.question('then press Enter here to continue… ');
  if (!(await loggedIn())) {
    console.error('Still not logged in — aborting.');
    await browser.close();
    process.exit(1);
  }
}
console.log('Logged in ✔');

// ── 2. collect liked-video links ────────────────────────────────────────
await page.goto(PROFILE_URL, {waitUntil: 'domcontentloaded'});
await sleep(3000);

const likedTab = page.locator('[data-e2e="liked-tab"]');
if ((await likedTab.count()) === 0) {
  console.error('Could not find the Liked tab — is this your own profile URL?');
  await browser.close();
  process.exit(1);
}
await likedTab.click();
await sleep(3000);

// scroll a bit to load enough items for this run
for (let i = 0; i < 5; i++) {
  await page.mouse.wheel(0, 2200);
  await sleep(1500);
}

const links = await page
  .locator('[data-e2e="user-liked-item"] a[href*="/video/"]')
  .evaluateAll((as) => [...new Set(as.map((a) => a.href))]);

if (links.length === 0) {
  console.log('No liked videos found (private list, empty, or selectors changed).');
  await browser.close();
  process.exit(0);
}

const targets = links.slice(0, MAX_PER_RUN);
console.log(`Found ${links.length} liked videos — unliking ${targets.length} this run.\n`);

// ── 3. unlike each ──────────────────────────────────────────────────────
let done = 0;
for (const url of targets) {
  try {
    await page.goto(url, {waitUntil: 'domcontentloaded'});
    await sleep(3500 + Math.random() * 2000);

    // captcha / verification wall → stop rather than fight it
    const blocked = await page
      .locator('#captcha-verify-image, .captcha_verify_container, [class*="captcha"]')
      .count();
    if (blocked > 0) {
      console.log('⚠ Captcha detected — stopping. Solve it manually and rerun later.');
      break;
    }

    // The like button on the watch page. aria-pressed tells us its state.
    const likeBtn = page
      .locator('button:has([data-e2e="browse-like-icon"]), [data-e2e="like-icon"]')
      .first();
    if ((await likeBtn.count()) === 0) {
      console.log(`? like button not found, skipping: ${url}`);
      continue;
    }

    const pressed = await likeBtn.getAttribute('aria-pressed');
    if (pressed === 'false') {
      console.log(`- already unliked: ${url}`);
    } else {
      await likeBtn.click();
      await sleep(1200);
      done++;
      console.log(`✔ unliked (${done}/${targets.length}): ${url}`);
    }
  } catch (err) {
    console.log(`✗ error on ${url}: ${err.message}`);
  }
  await humanDelay();
}

console.log(`\nDone — ${done} videos unliked this run.`);
console.log('Rerun later to continue (the Liked list refills the first page).');
await browser.close();
rl.close();
