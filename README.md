# MediaBox

> **Download, Organize, and Manage Your Media**

*Your Personal Media Manager — Fast. Secure. Organized.*

## About

MediaBox is a modern media management platform built with Python (FastAPI) and Vue.js. It provides a clean interface for managing authorized media downloads, tracking progress in real time, organizing files, and processing media with FFmpeg. The project demonstrates REST API development, asynchronous background jobs, file storage, and responsive frontend design.

## Local development

Create the backend environment on an executable filesystem (outside this
drive) and install dependencies:

```bash
python3 -m venv ~/.cache/mediabox/venv
~/.cache/mediabox/venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

Start both services with:

```bash
bash dev.sh
```

The API starts at port 8005 and the web UI at port 3005, using the next free
port when needed. Press Ctrl-C to stop both.

Local development uses the MySQL database `mediabox` on `127.0.0.1`.
Set its connection credentials in `backend/.env` using `backend/.env.example`
as a template. The launcher requires local MySQL and does not open a database
SSH tunnel. Development users, plans, and settings are separate from production,
which uses MySQL through `docker-compose.yml`. Create a local account when
using this database for the first time.

Use `bash dev.sh` on drives mounted with `noexec` (including this workspace's
DriveBeltie mount). Such mounts block `./dev.sh` even when it has executable
permissions.

On this machine, `frontend/node_modules` links to
`~/.cache/mediabox/frontend/node_modules` so Nuxt and native dependencies can
execute outside the `noexec` drive. The previous dependency directory is kept
at `frontend/.cache/node_modules-original`.

The launcher uses a working `backend/.venv` when available, then falls back to
`~/.cache/mediabox/venv` (or `$XDG_CACHE_HOME/mediabox/venv`). On this machine,
`backend/.venv` links to the home cache environment; the original is preserved
at `backend/.cache/venv-original`. The editor and `pyrightconfig.json` use
`backend/.venv`. Reload the editor window after changing the environment.

## DigitalOcean Spaces storage

Set `STORAGE_BACKEND=spaces` and the `DO_SPACES_*` values in `backend/.env`
to use private Spaces storage for the library. `APP_ENV=dev` keeps local test
objects separate from the production prefix. The default `STORAGE_BACKEND=local`
keeps local development working without Spaces credentials.

The existing library UI uses `/api/downloads/upload`; completed media,
conversions, cutouts, thumbnails, and photo slides are published to Spaces.
Downloads redirect to private links that expire after one hour. Processing
uses temporary local input files. Existing local library records still work.
Avatars, branding, and incomplete jobs continue to need the media directory.

The standalone endpoints are `POST /api/upload` (multipart `file`, requires
`media.create`) and `GET /api/url/{key}` (requires `media.view`). They return
an object key and a signed URL, respectively. These standalone uploads do
not create library records. Keys include the environment and owner ID.

See [production setup](docs/PRODUCTION.md#digitalocean-spaces) for server
settings, browser CORS, live verification, and existing-file migration.

## Production

Production settings for **https://droplinks.site** are in
`.env.production.example` and `docker-compose.production.yml`. See
[production setup](docs/PRODUCTION.md) for Gmail credentials, HTTPS, and the
commands for deploying while retaining existing database and media volumes.

## Taglines

- Download, Organize, and Manage Your Media
- Your Personal Media Manager
- Fast. Secure. Organized.
- Media Downloads Made Simple
- One Place for Your Media

## Tech Stack

| Layer            | Technology              |
|------------------|-------------------------|
| Backend          | Python + FastAPI        |
| Frontend         | Vue 3 + Nuxt 4          |
| Database         | PostgreSQL (or MySQL)   |
| Queue            | Redis + Celery          |
| Storage          | Local or AWS S3         |
| Media Processing | FFmpeg                  |
| Deployment       | Docker + Nginx          |

## Folder Structure

```
mediabox/
├── backend/
│   ├── app/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── workers/
│   └── main.py
│
├── frontend/
│   ├── pages/
│   ├── components/
│   └── composables/
│
├── docker/
├── docs/
└── docker-compose.yml
```

## Features (MVP)

- 🔐 User authentication
- 🌐 Submit a media URL (for supported and authorized sources)
- 📊 Download progress
- 📂 Download history
- 🖼️ Thumbnail preview
- 📁 File management
- 🔍 Search downloads
- ⭐ Favorite items
- 🌙 Dark modeth
- 📱 Responsive UI

## Implemented Beyond MVP

- ⚡ WebSocket live progress (with polling fallback)
- 📦 Batch URL submission
- 🔁 Resume interrupted downloads (HTTP Range)
- 🎞️ Media conversion with FFmpeg (mp4, webm, gif, mp3, m4a, wav)
- 🛠️ Admin dashboard (first registered user is admin)
- 📖 REST API documentation (Swagger at `/docs`)
- 📹 TikTok / Facebook / YouTube / Pornhub / Instagram video links resolved via yt-dlp (configurable allowlist; authorized content only)

Video-site links work in both the library and guest downloader. If you set
`YTDLP_HOSTS` in `backend/.env`, include `pornhub.com` to enable Pornhub links;
subdomains such as `www.pornhub.com` are included automatically. Restart the
backend after changing this setting. Videos that require login can use a
Netscape-format cookies file configured with `YTDLP_COOKIES_FILE`.

Instagram reel and video-post links use the same downloader, including shared
links with tracking parameters. If your server sets `YTDLP_HOSTS` explicitly,
add `instagram.com` to that list and restart the backend. For example:

```dotenv
YTDLP_HOSTS=tiktok.com,facebook.com,fb.watch,youtube.com,youtu.be,pornhub.com,instagram.com
```

If Instagram requests login, configure `YTDLP_COOKIES_FILE` with a
Netscape-format cookies file from an account that can access the video.

## Guest download settings

Full administrators can configure anonymous download quality at
**Settings → Guest downloads** (`/profile?tab=guest`). Choose any of Best, 4K,
1440p, 1080p, 720p, and 480p, then select a default from the enabled qualities.
The public page and download API follow the saved policy without a restart.
At least one quality must remain enabled. Existing defaults are 720p and 480p,
with 480p selected. Settings are stored in the existing database; no migration
is required. Deploy the updated backend and rebuild the frontend for this UI.

## Future Features

- Background download queue (Redis + Celery)
- Additional cloud storage providers (Google Drive)
