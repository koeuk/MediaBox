# MediaBox Guide Video

A ~65s animated feature-guide video for MediaBox, built with [Remotion](https://remotion.dev).
All UI shown is an animated mockup styled with MediaBox's real design tokens
(`frontend/app/assets/css/main.css`).

## Scenes

| # | Scene | Content |
|---|-------|---------|
| 1 | Intro | Logo + tagline typewriter |
| 2 | Download | "Add to your box": paste a URL, quality picker, live progress |
| 3 | Watch | Preview dialog: player, auto-next, filmstrip, 9/58 counter |
| 4 | Organize | Status tabs + category pills, filtering, star favorites |
| 5 | Convert | CONVERT dropdown → gif with FFmpeg progress |
| 6 | Outro | Feature recap + tech stack end card |

## Commands

```bash
npm install
npm run dev      # open Remotion Studio to preview/edit
npm run render   # render to out/mediabox-guide.mp4
```

Scene timing lives in `src/Root.tsx` (30 fps, 1920×1080). Shared UI pieces
(app window, navbar, cursor, progress bar, captions) are in `src/ui.tsx`;
design tokens in `src/theme.ts`.
