# TikTok Unliker

Personal utility that bulk-unlikes posts on **your own** TikTok account by
driving Google Chrome through Playwright. A profile link alone can't do this —
write actions need your logged-in session, so the script opens a browser
where you sign in once; the session is saved in `./session/` for later runs.

> ⚠️ Automated interaction is against TikTok's Terms of Service. On your own
> account the usual consequences are captchas or temporary action-blocks,
> but you run it at your own risk. Keep runs small and slow.

## Setup (once)

```bash
cd tools/tiktok-unliker
npm install
```

The script opens installed Google Chrome by default (`BROWSER_CHANNEL=chrome`).
If you want to use Playwright bundled Chromium instead, run
`npx playwright install chromium` once, then start with `BROWSER_CHANNEL= npm start`.

## Check Without Unliking

Use dry-run mode first. It opens TikTok, collects liked posts, visits the first
few, and prints what it would unlike without clicking the like button.

```bash
DRY_RUN=1 MAX_PER_RUN=5 TIKTOK_PROFILE=https://www.tiktok.com/@yourname npm start
```

## Run

```bash
TIKTOK_PROFILE=https://www.tiktok.com/@yourname npm start
```

- First run: a browser window opens — log in to TikTok, then press Enter in
  the terminal. Later runs reuse the saved session.
- It opens your Liked tab, collects post links, and unlikes up to
  `MAX_PER_RUN` (default 50) with random delays between each.
- It stops immediately if a captcha appears — solve it manually, rerun later.
- Rerun as many times as needed; each run works through the next batch.

To clear the whole Liked list in one go, use `UNLIKE_ALL=1` — it keeps
cycling (collect → unlike → re-check) until the list is empty:

```bash
UNLIKE_ALL=1 TIKTOK_PROFILE=https://www.tiktok.com/@yourname npm start
```

Options via env vars:

```bash
DRY_RUN=1 MAX_PER_RUN=5 SCROLL_PASSES=2 npm start
MAX_PER_RUN=30 DELAY_MIN_S=10 DELAY_MAX_S=25 TIKTOK_PROFILE=... npm start
TIKTOK_SESSION_DIR=./another-session npm start
BROWSER_CHANNEL=chrome-beta npm start
BROWSER_EXECUTABLE_PATH=/usr/bin/google-chrome npm start
BROWSER_CHANNEL= npm start
```

## Notes

- Your Liked tab must be visible to you (it is, on your own profile).
- TikTok changes its DOM regularly. If nothing is found, the selectors in
  `unlike.mjs` (`liked-tab`, `user-liked-item`, `browse-like-icon`,
  `like-icon`) are the first thing to check in DevTools.
- `./session/` contains your TikTok login — don't commit or share it.
