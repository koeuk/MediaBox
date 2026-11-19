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

Use `bash dev.sh` on drives mounted with `noexec` (including this workspace's
DriveBeltie mount). Such mounts block `./dev.sh` even when it has executable
permissions.

The launcher uses a working `backend/.venv` when available, then falls back to
`~/.cache/mediabox/venv` (or `$XDG_CACHE_HOME/mediabox/venv`). The editor defaults
to the home cache environment. If an interpreter was already selected, run
**Python: Select Interpreter** and choose `~/.cache/mediabox/venv/bin/python`.

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
- 📹 TikTok / Facebook / YouTube / Pornhub video links resolved via yt-dlp (configurable allowlist; authorized content only)

Video-site links work in both the library and guest downloader. If you set
`YTDLP_HOSTS` in `backend/.env`, include `pornhub.com` to enable Pornhub links;
subdomains such as `www.pornhub.com` are included automatically. Restart the
backend after changing this setting. Videos that require login can use a
Netscape-format cookies file configured with `YTDLP_COOKIES_FILE`.

## Future Features

- Background download queue (Redis + Celery)
- Cloud storage integration (S3, Google Drive)
