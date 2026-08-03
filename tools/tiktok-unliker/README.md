# TikTok Unliker

Personal utility that bulk-unlikes videos on **your own** TikTok account by
driving a real browser (Playwright). A profile link alone can't do this —
write actions need your logged-in session, so the script opens a browser
where you sign in once; the session is saved in `./session/` for later runs.

> ⚠️ Automated interaction is against TikTok's Terms of Service. On your own
> account the usual consequences are captchas or temporary action-blocks,
> but you run it at your own risk. Keep runs small and slow.

## Setup (once)

```bash
cd tools/tiktok-unliker
npm install
npx playwright install chromium
```

## Run

```bash
TIKTOK_PROFILE=https://www.tiktok.com/@yourname npm start
```

- First run: a browser window opens — log in to TikTok, then press Enter in
  the terminal. Later runs reuse the saved session.
- It opens your Liked tab, collects video links, and unlikes up to
  `MAX_PER_RUN` (default 50) with 8–18 s random delays between each.
- It stops immediately if a captcha appears — solve it manually, rerun later.
- Rerun as many times as needed; each run works through the next batch.

Options via env vars: `MAX_PER_RUN=30 TIKTOK_PROFILE=… npm start`

## Notes

- Your Liked tab must be visible to you (it is, on your own profile).
- TikTok changes its DOM regularly. If nothing is found, the `data-e2e`
  selectors in `unlike.mjs` (`liked-tab`, `user-liked-item`,
  `browse-like-icon`) are the first thing to check in DevTools.
- `./session/` contains your TikTok login — don't commit or share it.
