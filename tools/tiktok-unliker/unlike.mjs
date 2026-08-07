// TikTok bulk-unliker — personal utility for YOUR OWN account only.
//
// How it works:
//   1. Opens a real (headful) Chrome with a persistent profile in ./session.
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

// ── config ──────────────────────────────────────────────────────────────
const PROFILE_URL = process.env.TIKTOK_PROFILE ?? 'https://www.tiktok.com/@koeuk1';
const MAX_PER_RUN = envNumber('MAX_PER_RUN', 50, {min: 1});
const SCROLL_PASSES = envNumber('SCROLL_PASSES', 5, {min: 0});
const DELAY_MIN_S = envNumber('DELAY_MIN_S', 8, {min: 0}); // seconds between unlikes (min)
const DELAY_MAX_S = Math.max(DELAY_MIN_S, envNumber('DELAY_MAX_S', 18, {min: 0}));
const DRY_RUN = envFlag('DRY_RUN');
const UNLIKE_ALL = envFlag('UNLIKE_ALL'); // keep cycling until the Liked list is empty
const SESSION_DIR = process.env.TIKTOK_SESSION_DIR ?? './session';
const BROWSER_CHANNEL = process.env.BROWSER_CHANNEL ?? 'chrome';
const BROWSER_EXECUTABLE_PATH = process.env.BROWSER_EXECUTABLE_PATH;
// ────────────────────────────────────────────────────────────────────────

// TikTok shows "Log in" buttons to logged-out visitors, but their exact
// selectors vary by layout — match by text as well as known ids.
const LOGGED_OUT_SELECTOR = [
  '#header-login-button',
  '[data-e2e="top-login-button"]',
  'button[data-e2e="nav-login-button"]',
  'button:has-text("Log in")',
  'a:has-text("Log in")',
].join(', ');

const LIKED_TAB_SELECTORS = [
  '[data-e2e="liked-tab"]',
  '[role="tab"]:has-text("Liked")',
  'button:has-text("Liked")',
  'a[href$="/liked"]',
];

const POST_LINK_SELECTORS = [
  '[data-e2e="user-liked-item"] a[href*="/video/"]',
  '[data-e2e="user-liked-item"] a[href*="/photo/"]',
  'a[href*="/video/"]',
  'a[href*="/photo/"]',
];

const LIKE_BUTTON_SELECTORS = [
  'button:has([data-e2e="browse-like-icon"])',
  'button:has([data-e2e="like-icon"])',
  'button[aria-pressed][aria-label*="like"]',
  'button[aria-pressed][aria-label*="Like"]',
  'button[aria-label*="like"]',
  'button[aria-label*="Like"]',
  '[data-e2e="browse-like-icon"]',
  '[data-e2e="like-icon"]',
];

function envNumber(name, fallback, {min}) {
  const value = Number(process.env[name] ?? fallback);
  return Number.isFinite(value) && value >= min ? value : fallback;
}

function envFlag(name) {
  return ['1', 'true', 'yes', 'on'].includes(String(process.env[name] ?? '').toLowerCase());
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const humanDelay = () =>
  sleep((DELAY_MIN_S + Math.random() * (DELAY_MAX_S - DELAY_MIN_S)) * 1000);

function browserLaunchOptions() {
  const options = {
    headless: false,
    viewport: {width: 1280, height: 850},
    // Plain Playwright Chrome advertises itself as automated
    // (navigator.webdriver, "controlled by automated software" banner),
    // which makes TikTok captcha-loop and log out the session. Present as a
    // normal browser instead.
    ignoreDefaultArgs: ['--enable-automation'],
    args: ['--disable-blink-features=AutomationControlled'],
  };

  if (BROWSER_EXECUTABLE_PATH) {
    options.executablePath = BROWSER_EXECUTABLE_PATH;
  } else if (BROWSER_CHANNEL) {
    options.channel = BROWSER_CHANNEL;
  }

  return options;
}

async function firstVisible(page, selectors, timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const selector of selectors) {
      const locator = page.locator(selector).first();
      if ((await locator.count()) === 0) continue;

      try {
        if (await locator.isVisible({timeout: 250})) return locator;
      } catch {
        // Try the next selector; TikTok often swaps DOM nodes while loading.
      }
    }
    await sleep(250);
  }

  return null;
}

// TikTok pages sometimes hold the connection open well past the default
// 30s navigation timeout, especially right after login. Retry once and
// settle for whatever has rendered rather than crashing.
async function gotoWithRetry(page, url) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      await page.goto(url, {waitUntil: 'domcontentloaded', timeout: 60000});
      return;
    } catch (err) {
      console.log(`  (slow load${attempt === 0 ? ', retrying' : ''}: ${err.message.split('\n')[0]})`);
    }
  }
}

async function loggedIn(page) {
  // No session cookie → definitely logged out.
  const cookies = await page.context().cookies('https://www.tiktok.com');
  if (!cookies.some((c) => c.name === 'sessionid' && c.value)) return false;

  // A stale cookie can survive a server-side logout — the page then still
  // renders visible "Log in" buttons.
  const loginButton = page.locator(LOGGED_OUT_SELECTOR).first();
  if ((await loginButton.count()) > 0 && (await loginButton.isVisible().catch(() => false))) {
    return false;
  }
  return true;
}

// TikTok's slider-puzzle captcha needs a human. If one is up, tell the user
// to solve it in the browser window and poll until it disappears.
async function waitForCaptchaClear(page, maxWaitS = 300) {
  const present = async () =>
    (await page.locator('#captcha-verify-image, .captcha_verify_container, [class*="captcha_verify"]').count()) > 0 ||
    (await page.getByText('Drag the slider', {exact: false}).count()) > 0;

  if (!(await present())) return true;

  console.log('\n⚠ Captcha detected — solve the puzzle in the browser window.');
  console.log(`  Waiting up to ${maxWaitS}s for it to clear…`);

  const deadline = Date.now() + maxWaitS * 1000;
  while (Date.now() < deadline) {
    await sleep(3000);
    if (!(await present())) {
      console.log('Captcha cleared ✔\n');
      await sleep(1500);
      return true;
    }
  }

  console.log('Captcha still up after the wait — stopping this run.');
  return false;
}

// TikTok shows post-login popups (notifications, app promos) in TUXModal /
// floating-ui portals that swallow clicks anywhere on the page. Close them
// via their close buttons, then Escape as a fallback.
async function dismissPopups(page) {
  const closeSelectors = [
    '[data-e2e="modal-close-inner-button"]',
    '.TUXModal [aria-label="Close"]',
    '.TUXModal [aria-label="close"]',
    '[data-floating-ui-portal] [aria-label*="lose"]',
    'div[role="dialog"] button[aria-label*="lose"]',
  ];

  for (let round = 0; round < 3; round++) {
    let closedAny = false;
    for (const selector of closeSelectors) {
      const button = page.locator(selector).first();
      if ((await button.count()) === 0) continue;
      if (!(await button.isVisible().catch(() => false))) continue;

      await button.click({timeout: 2000}).catch(() => {});
      closedAny = true;
      await sleep(600);
    }

    const overlays = await page
      .locator('.TUXModal-overlay, [data-floating-ui-portal] [role="dialog"]')
      .count();
    if (overlays === 0) return;

    await page.keyboard.press('Escape').catch(() => {});
    await sleep(600);
    if (!closedAny && round > 0) return; // nothing closable left — give up quietly
  }
}

async function collectPostLinks(page) {
  return page.evaluate((selectors) => {
    const urls = new Set();
    for (const selector of selectors) {
      for (const link of document.querySelectorAll(selector)) {
        const href = link.href || link.getAttribute('href');
        if (!href) continue;

        try {
          const url = new URL(href, location.origin);
          if (/\/(video|photo)\/\d+/.test(url.pathname)) {
            url.search = '';
            url.hash = '';
            urls.add(url.href);
          }
        } catch {
          // Ignore non-URL hrefs.
        }
      }
    }
    return [...urls];
  }, POST_LINK_SELECTORS);
}

async function findLikeControl(page) {
  for (const selector of LIKE_BUTTON_SELECTORS) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) === 0) continue;

    const handle = await locator.elementHandle().catch(() => null);
    if (!handle) continue;

    const buttonHandle = await handle.evaluateHandle((el) => el.closest('button') ?? el);
    const element = buttonHandle.asElement();
    if (!element) continue;

    const visible = await element.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
    });
    if (visible) return {element, selector};
  }

  return null;
}

async function likeState(element) {
  return element.evaluate((el) => {
    const button = el.closest('button') ?? el;
    const ariaPressed = button.getAttribute('aria-pressed');
    if (ariaPressed === 'true') return 'liked';
    if (ariaPressed === 'false') return 'unliked';

    const label = `${button.getAttribute('aria-label') ?? ''} ${button.getAttribute('title') ?? ''}`.toLowerCase();
    if (label.includes('unlike')) return 'liked';
    if (/\blike\b/.test(label)) return 'unliked';

    const icon = button.querySelector('[data-e2e*="like-icon"], svg') ?? button;
    const style = getComputedStyle(icon);
    const fill = style.fill || icon.getAttribute('fill') || '';
    const color = style.color || '';
    const isTikTokRed = (value) => /rgb\(\s*254\s*,\s*44\s*,\s*85\s*\)|#fe2c55/i.test(value);
    if (isTikTokRed(fill) || isTikTokRed(color)) return 'liked';

    return 'unknown';
  });
}

async function run(page) {
  if (DRY_RUN) {
    console.log('Dry run enabled — collecting and checking only; no videos will be unliked.');
  }

  // ── 1. ensure logged in ───────────────────────────────────────────────
  await gotoWithRetry(page, 'https://www.tiktok.com/');
  await sleep(3000);

  if (!(await loggedIn(page))) {
    console.log('\nNot logged in. Log in to TikTok in the browser window —');
    console.log('waiting up to 5 minutes for the login to complete…');

    const deadline = Date.now() + 300_000;
    while (Date.now() < deadline && !(await loggedIn(page))) {
      await sleep(3000);
    }

    if (!(await loggedIn(page))) {
      console.error('Still not logged in — aborting.');
      process.exitCode = 1;
      return;
    }
  }
  console.log('Logged in ✔');

  // ── 2. collect & unlike — one batch, or cycles until empty with UNLIKE_ALL
  const perCycleCap = UNLIKE_ALL ? Infinity : MAX_PER_RUN;
  let totalDone = 0;
  let aborted = false;

  for (let cycle = 1; !aborted; cycle++) {
    await gotoWithRetry(page, PROFILE_URL);
    await sleep(3000);

    if (!(await waitForCaptchaClear(page))) {
      process.exitCode = 1;
      break;
    }
    await dismissPopups(page);

    const likedTab = await firstVisible(page, LIKED_TAB_SELECTORS, 10000);
    if (!likedTab) {
      console.error('Could not find the Liked tab — is this your own profile URL, and is the Liked tab visible?');
      process.exitCode = 1;
      break;
    }

    try {
      await likedTab.click({timeout: 10000});
    } catch {
      // A popup may have reappeared over the tab — dismiss and retry once.
      await dismissPopups(page);
      await likedTab.click({timeout: 10000});
    }
    await sleep(3000);

    const seen = new Set();
    for (let i = 0; i <= SCROLL_PASSES; i++) {
      for (const link of await collectPostLinks(page)) seen.add(link);
      if (seen.size >= perCycleCap || i === SCROLL_PASSES) break;

      await page.mouse.wheel(0, 2200);
      await sleep(1500);
    }

    const links = [...seen];
    if (links.length === 0) {
      console.log(
        cycle === 1
          ? 'No liked videos found (private list, empty, or selectors changed).'
          : 'Liked list is empty now — all done.'
      );
      break;
    }

    const targets = UNLIKE_ALL ? links : links.slice(0, MAX_PER_RUN);
    const prefix = UNLIKE_ALL ? `Cycle ${cycle}: found` : 'Found';
    console.log(`${prefix} ${links.length} liked posts — ${DRY_RUN ? 'checking' : 'unliking'} ${targets.length}.\n`);

    // ── 3. unlike each ──────────────────────────────────────────────────
    let done = 0;
    for (const url of targets) {
      try {
        await gotoWithRetry(page, url);
        await sleep(3500 + Math.random() * 2000);

        // captcha / verification wall → give the user a chance to solve it
        if (!(await waitForCaptchaClear(page))) {
          aborted = true;
          break;
        }

        // A logged-out page shows every like button as "not liked", which
        // would make us skip posts that are actually still liked.
        if (!(await loggedIn(page))) {
          console.log('⚠ Session got logged out — stopping. Log in again and rerun.');
          aborted = true;
          break;
        }

        await dismissPopups(page);

        const likeControl = await findLikeControl(page);
        if (!likeControl) {
          console.log(`? like button not found, skipping: ${url}`);
          continue;
        }

        const state = await likeState(likeControl.element);
        if (state === 'unliked') {
          console.log(`- already unliked: ${url}`);
          continue;
        }

        if (DRY_RUN) {
          console.log(`• would unlike (${state}, via ${likeControl.selector}): ${url}`);
          continue;
        }

        await likeControl.element.click({timeout: 5000});
        await sleep(1200);

        const refreshedControl = await findLikeControl(page);
        const newState = refreshedControl ? await likeState(refreshedControl.element) : 'unknown';
        done++;
        console.log(`✔ unliked (${done}/${targets.length}, now ${newState}): ${url}`);
      } catch (err) {
        if (/has been closed/.test(err.message)) {
          console.log('\n⚠ Browser window was closed — stopping.');
          aborted = true;
          break;
        }
        console.log(`✗ error on ${url}: ${err.message}`);
      }
      await humanDelay();
    }
    totalDone += done;

    if (DRY_RUN || !UNLIKE_ALL) break;
    if (!aborted && done === 0) {
      // Everything left in the list read as already-unliked (stale entries) —
      // another cycle would just spin on the same posts.
      console.log('\nNo posts actually unliked this cycle — stopping.');
      break;
    }
    if (!aborted) {
      console.log(`\nCycle ${cycle} finished — ${done} unliked (${totalDone} total). Rechecking the Liked list…`);
    }
  }

  console.log(`\nDone — ${DRY_RUN ? '0 videos unliked in dry run' : `${totalDone} videos unliked${UNLIKE_ALL ? '' : ' this run'}`}.`);
  if (!UNLIKE_ALL && !DRY_RUN) {
    console.log('Rerun later to continue (the Liked list refills the first page), or use UNLIKE_ALL=1 to clear everything in one go.');
  }
}

if (!PROFILE_URL) {
  console.error('Set your profile first, e.g.:');
  console.error('  TIKTOK_PROFILE=https://www.tiktok.com/@yourname npm start');
  process.exit(1);
}

const browserName = BROWSER_EXECUTABLE_PATH || BROWSER_CHANNEL || 'bundled Chromium';
console.log('Opening ' + browserName + ' with profile ' + SESSION_DIR);
const browser = await chromium.launchPersistentContext(SESSION_DIR, browserLaunchOptions());
const page = browser.pages()[0] ?? (await browser.newPage());

try {
  await run(page);
} catch (err) {
  if (/has been closed/.test(err.message)) {
    console.log('\n⚠ Browser window was closed — stopping.');
  } else {
    throw err;
  }
} finally {
  await browser.close().catch(() => {});
}
