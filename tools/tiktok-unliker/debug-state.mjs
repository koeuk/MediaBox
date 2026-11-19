// Temporary debug helper: open one video and watch the like button's state
// over time to see whether "already unliked" reads are real or premature.
import {chromium} from 'playwright';

const URL = process.argv[2] ?? 'https://www.tiktok.com/@hon6867/video/7668935893901888786';
const SHOT = '/tmp/claude-1000/-home-koeuk-Projects-MediaBox/1a59b486-a6b9-42c2-91fc-78455977333a/scratchpad/like-state.png';

const browser = await chromium.launchPersistentContext('./session', {
  headless: false,
  channel: 'chrome',
  viewport: {width: 1280, height: 850},
  ignoreDefaultArgs: ['--enable-automation'],
  args: ['--disable-blink-features=AutomationControlled'],
});
const page = browser.pages()[0] ?? (await browser.newPage());
await page.goto(URL, {waitUntil: 'domcontentloaded'});

for (let t = 0; t <= 12; t += 3) {
  const info = await page.evaluate(() => {
    const results = [];
    for (const sel of ['button:has([data-e2e="browse-like-icon"])', '[data-e2e="browse-like-icon"]', '[data-e2e="like-icon"]']) {
      let el;
      try { el = document.querySelector(sel); } catch { continue; }
      if (!el) continue;
      const button = el.closest('button') ?? el;
      const icon = button.querySelector('[data-e2e*="like-icon"], svg') ?? button;
      const style = getComputedStyle(icon);
      results.push({
        sel,
        ariaPressed: button.getAttribute('aria-pressed'),
        ariaLabel: button.getAttribute('aria-label'),
        fill: style.fill,
        color: style.color,
        html: button.outerHTML.slice(0, 300),
      });
      break;
    }
    return {results, captcha: document.querySelectorAll('[class*="captcha_verify"]').length};
  });
  console.log(`t=${t}s`, JSON.stringify(info, null, 2));
  if (t < 12) await page.waitForTimeout(3000);
}

await page.screenshot({path: SHOT});
console.log('screenshot:', SHOT);
await browser.close();
