// Temporary debug helper: open the Liked tab, screenshot it, and report
// what the collector selectors actually match.
import {chromium} from 'playwright';

const PROFILE_URL = process.env.TIKTOK_PROFILE ?? 'https://www.tiktok.com/@koeuk1';
const SHOT = process.env.SHOT_PATH ?? '/tmp/claude-1000/-home-koeuk-Projects-MediaBox/1a59b486-a6b9-42c2-91fc-78455977333a/scratchpad/liked-tab.png';

const browser = await chromium.launchPersistentContext('./session', {
  headless: false,
  channel: 'chrome',
  viewport: {width: 1280, height: 850},
});
const page = browser.pages()[0] ?? (await browser.newPage());

await page.goto(PROFILE_URL, {waitUntil: 'domcontentloaded'});
await page.waitForTimeout(4000);

const likedTab = page.locator('[data-e2e="liked-tab"]').first();
console.log('liked-tab count:', await likedTab.count());
if (await likedTab.count()) {
  await likedTab.click().catch((e) => console.log('tab click error:', e.message));
  await page.waitForTimeout(5000);
}

console.log('url now:', page.url());

const counts = await page.evaluate(() => {
  const q = (s) => document.querySelectorAll(s).length;
  return {
    likedItems: q('[data-e2e="user-liked-item"]'),
    videoLinks: q('a[href*="/video/"]'),
    photoLinks: q('a[href*="/photo/"]'),
    postItems: q('[data-e2e="user-post-item"]'),
    captcha: q('#captcha-verify-image, .captcha_verify_container, [class*="captcha"]'),
    bodySnippet: document.body.innerText.slice(0, 600),
  };
});
console.log(JSON.stringify(counts, null, 2));

await page.screenshot({path: SHOT, fullPage: false});
console.log('screenshot saved:', SHOT);

await browser.close();
