# MediaBox

> **Download, Organize, and Manage Your Media**

*Your Personal Media Manager — Fast. Secure. Organized.*

## About

MediaBox is a modern media management platform built with Python (FastAPI) and Vue.js. It provides a clean interface for managing authorized media downloads, tracking progress in real time, organizing files, and processing media with FFmpeg. The project demonstrates REST API development, asynchronous background jobs, file storage, and responsive frontend design.

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
- 📹 TikTok / Facebook video links resolved via yt-dlp (configurable allowlist; authorized content only)

## Future Features

- Background download queue (Redis + Celery)
- Cloud storage integration (S3, Google Drive)
