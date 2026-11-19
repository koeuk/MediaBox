# MediaBox — Developer Guide

Current state: the **backend, frontend, and Docker/Nginx setup are implemented**. This guide covers what exists, how to run it, and the roadmap of future features.

## What's Implemented (Backend)

```
backend/
├── app/
│   ├── main.py               # FastAPI app, CORS, routers, /api/health
│   ├── config.py             # Settings via env vars / .env file
│   ├── database.py           # SQLAlchemy engine + session (SQLite default; Postgres/MySQL ready)
│   ├── security.py           # Password hashing (pbkdf2) + JWT create/decode
│   ├── schemas.py            # Pydantic request/response models
│   ├── models/
│   │   ├── user.py           # User table
│   │   └── download.py       # Download table + status enum
│   ├── api/
│   │   ├── deps.py           # get_current_user (Bearer) + get_media_user (?token=, media-scoped)
│   │   ├── auth.py           # /register, /login, /me, /media-token
│   │   └── downloads.py      # CRUD + file/thumbnail serving
│   └── services/
│       ├── jobs.py           # bounded worker pool (MAX_CONCURRENT_DOWNLOADS)
│       └── downloader.py     # Streaming download worker + FFmpeg thumbnails
├── requirements.txt
├── Dockerfile                # python:3.12-slim + ffmpeg
└── .env.example
```

### Features working

- JWT auth (register / login / me), passwords hashed with pbkdf2_sha256
- Submit a URL → streamed to disk in a background task with live progress persisted to the DB (poll `GET /api/downloads/{id}`)
- Download size cap (`MAX_DOWNLOAD_SIZE_MB`, default 2048)
- Thumbnails generated with FFmpeg for images and videos
- Search (`?search=`), favorites toggle, delete (removes files too)
- File + thumbnail endpoints accept `?token=` so `<img>`/`<a>` tags work — but only
  short-lived media tokens from `POST /api/auth/media-token` (10 min), never the main JWT
- SSRF guard: download URLs resolving to private/internal addresses are rejected
  (set `ALLOW_PRIVATE_URLS=true` in local dev to test with localhost URLs)
- Downloads/conversions run on a bounded worker pool (`MAX_CONCURRENT_DOWNLOADS`,
  default 3); excess jobs wait in the queue as `queued`. Jobs in flight during a
  server restart are marked failed and can be resumed with retry.
- Video links from allowlisted sites (`YTDLP_HOSTS`, default TikTok/Facebook/YouTube)
  are resolved with **yt-dlp** instead of a direct stream; everything else still
  needs a direct file URL. Only download content you own or are authorized to save —
  many Facebook videos additionally require login and will fail as private.
  For login-gated videos (e.g. age-restricted posts) set `YTDLP_COOKIES_FILE` to a
  Netscape cookies.txt exported from your browser. YouTube extraction needs a JS
  runtime on the host (`node` or `deno` — auto-detected).

## Running the Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # edit SECRET_KEY etc.
uvicorn app.main:app --reload
```

- API: http://localhost:8000/api/health
- Interactive docs (Swagger): http://localhost:8000/docs
- FFmpeg must be installed for thumbnails (`sudo apt install ffmpeg`) — downloads still work without it.
- Default DB is SQLite (`backend/mediabox.db`).
  - Postgres: `DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/mediabox`
  - MySQL: `DATABASE_URL=mysql+pymysql://user:pass@127.0.0.1:3306/mediabox?charset=utf8mb4`
    (the `charset=utf8mb4` is required so emoji/Khmer titles store correctly).
    Create the DB with `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`.
  - To move existing SQLite data into MySQL, set the MySQL `DATABASE_URL` then run
    `.venv/bin/python migrate_to_mysql.py` (copies users + downloads; refuses if the
    target already has data). Tables are auto-created on first boot.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/auth/register` | `{email, username, password}` → token + user |
| POST   | `/api/auth/login` | `{email, password}` → token + user |
| GET    | `/api/auth/me` | Current user |
| POST   | `/api/auth/media-token` | Short-lived (10 min) media-scoped token for `?token=` URLs |
| POST   | `/api/downloads` | `{url, title?}` → queues download, returns record |
| POST   | `/api/downloads/batch` | `{urls: [..max 50]}` → queues many, returns records |
| POST   | `/api/downloads/upload` | multipart `file` (video/audio/image) → completed record, ready to preview/convert |
| GET    | `/api/downloads?search=&favorites=` | List own downloads (newest first) |
| GET    | `/api/downloads/{id}` | Single record (poll this for progress) |
| POST   | `/api/downloads/{id}/retry` | Retry a failed download (resumes via HTTP Range when the server supports it) |
| POST   | `/api/downloads/{id}/convert` | `{target: mp4\|webm\|gif\|mp3\|m4a\|wav}` → new record, FFmpeg converts in background |
| PATCH  | `/api/downloads/{id}/favorite` | Toggle favorite |
| DELETE | `/api/downloads/{id}` | Delete record + files |
| GET    | `/api/downloads/{id}/file?token=` | Download the stored file |
| GET    | `/api/downloads/{id}/thumbnail?token=` | JPEG thumbnail |
| WS     | `/api/ws/progress?token=` | Pushes `{type:"snapshot", items:[...]}` whenever the list changes (~1s) |
| GET    | `/api/admin/stats` | Admin only — user/download/status/storage totals |
| GET    | `/api/admin/users` | Admin only — users with download counts + storage |
| GET    | `/api/admin/downloads?limit=` | Admin only — recent downloads across all users |

All `/api/downloads` endpoints require `Authorization: Bearer <token>`. The two file endpoints and the WebSocket also accept `?token=`, but only a **media token** from `/api/auth/media-token` — the long-lived JWT is rejected there so it never appears in URLs, server logs, or browser history. The **first registered user automatically becomes the admin**; the `/admin` page in the frontend is visible only to admins.

> ⚠️ **Do not run the servers with `sudo`.** A root-run server creates root-owned `mediabox.db` and `media/` files that break later non-root runs. If that happened, fix with:
> `sudo chown -R $USER:$USER backend/media backend/mediabox.db`

> ℹ️ **Only direct media-file URLs work** (links ending in the actual file, e.g. `.../video.mp4`). Page URLs from sites like YouTube download the page's HTML, not the video — YouTube doesn't permit downloading its videos outside its own apps, and MediaBox deliberately does not extract from such sites.

### Quick smoke test

```bash
# register
curl -s -X POST localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","username":"me","password":"secret123"}'

# submit a download (replace TOKEN)
curl -s -X POST localhost:8000/api/downloads \
  -H "Authorization: Bearer TOKEN" -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/file.jpg"}'
```

## What's Implemented (Frontend)

```
frontend/
├── nuxt.config.ts            # runtimeConfig.public.apiBase → http://localhost:8000/api
├── package.json              # nuxt ^4, vue ^3.5 (no other runtime deps)
├── Dockerfile                # node:22-alpine, builds .output, runs nitro server
└── app/
    ├── app.vue               # shell + theme cookie (dark default, light toggle)
    ├── assets/css/main.css   # design tokens, buttons/inputs/badges, grain overlay
    ├── composables/
    │   ├── useApi.ts         # $fetch wrapper attaching the Bearer token + fileUrl()
    │   └── useAuth.ts        # token cookie + user state, login/register/logout
    ├── middleware/auth.ts    # redirect to /login when no token
    ├── pages/
    │   ├── index.vue         # URL submit bar, all/favorites/active filters, search, card grid, 2s polling
    │   ├── login.vue
    │   └── register.vue
    └── components/
        ├── AppNavbar.vue     # wordmark, username, theme toggle, logout
        └── DownloadCard.vue  # thumbnail, progress bar, favorite, save, delete
```

Key decisions:
- Auth token stored in a cookie (`useCookie`) so SSR works.
- Progress via polling `GET /api/downloads` every 2s while any item is queued/downloading (WebSocket is a future upgrade).
- Thumbnails/file links use the `?token=` query param.
- Design: dark-first "media vault" theme (Archivo + IBM Plex Mono, amber accent), light mode via `data-theme` attribute.

### Running the Frontend

```bash
cd frontend
npm install --legacy-peer-deps   # plain `npm install` can hit an npm arborist bug (edgesOut)
npm run dev                      # http://localhost:3000
```

The API base defaults to `http://localhost:8000/api`; override with `NUXT_PUBLIC_API_BASE` (Docker sets it to `/api` so requests go through nginx).

End-to-end tested with Playwright: register → submit URL → live progress → completed card with thumbnail → favorite/filter/search → theme toggle → logout.

## Docker / Deployment

- `docker-compose.yml`: `db` (postgres:16-alpine), `backend`, `frontend`, `nginx` (port 80, override with `HTTP_PORT`).
- `docker/nginx.conf`: proxy `/api` → `backend:8000`, everything else → `frontend:3000`.
- Named volumes: `pgdata`, `media_data` (mounted at `/app/media` in backend).
- Set `SECRET_KEY` and `POSTGRES_PASSWORD` in a root `.env` before deploying.

```bash
docker compose up --build   # app at http://localhost
```

## Implemented feature upgrades

- ✅ WebSocket live progress (`/api/ws/progress`) — the dashboard shows a **live** indicator when connected and falls back to 2s polling otherwise
- ✅ Batch URL submission — paste multiple space/comma-separated URLs in the submit bar
- ✅ Retry failed downloads with HTTP-Range resume (partial files are kept on disk)
- ✅ FFmpeg conversion (mp4 / webm / gif / mp3 / m4a / wav) with real progress tracked from ffmpeg's `-progress` output
- ✅ Admin dashboard (`/admin`) — stat tiles, per-user storage, recent downloads

## Roadmap — Future features

- Redis + Celery to replace FastAPI BackgroundTasks (survives restarts, retries)
- S3 storage backend behind a storage interface

## Configuration Reference

| Env var | Default | Notes |
|---------|---------|-------|
| `SECRET_KEY` | change-me-in-production | JWT signing key — change it |
| `DATABASE_URL` | `sqlite:///./mediabox.db` | Postgres/MySQL URL for production |
| `MEDIA_DIR` | `./media` | Files stored under `media/<user_id>/` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated |
| `MAX_DOWNLOAD_SIZE_MB` | `2048` | Enforced before and during streaming |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 10080 (7 days) | Token lifetime |
