# Running MediaBox locally

## TL;DR

```bash
cd ~/Projects/MediaBox
./dev.sh
```

Then open **http://localhost:3005**. Press `Ctrl-C` to stop both servers.

> **Never run this with `sudo`.** See [Never use sudo](#never-use-sudo) below —
> it is the single most common way to break this project.

---

## What `./dev.sh` does

It starts both halves of the app together:

| Service        | URL                              | What it is                   |
| -------------- | -------------------------------- | ---------------------------- |
| Web UI (Nuxt)  | http://localhost:3005            | what you open in the browser |
| API (FastAPI)  | http://localhost:8005/api/health | the backend                  |

Both are needed — the UI is useless without the API.

**Ports are starting points, not requirements.** If 8005 or 3005 is taken, the
next free port is used and you'll see a line like:

```
port 3005 busy — web moved to 3006
```

The script points the frontend at whichever port the API actually got, and
tells the API to accept that origin, so the two can never drift apart.

To start looking from different ports:

```bash
API_PORT=9001 WEB_PORT=4000 ./dev.sh
```

Before starting, it refuses to run if:

1. You are root (see below)
2. The virtualenv or `node_modules` is missing
3. Build caches are owned by another user

---

## Never use sudo

Running the servers as root makes every downloaded file **root-owned**. You
then cannot delete your own downloads from the file manager — they show a
padlock — and the frontend build cache breaks with `EACCES` errors.

`./dev.sh` refuses to start as root. If you see:

```
error: Do not run this with sudo.
```

…check your prompt. If it says `root@…#` instead of `koeuk@…$`, you are in a
root shell — type `exit` until you are back to your normal user, then run it
again. `whoami` should print `koeuk`.

If files are already root-owned, fix them once:

```bash
sudo chown -R "$USER":"$USER" ~/Projects/MediaBox ~/Videos/video-download
```

---

## First-time setup

Only needed once, or after cloning fresh.

**Requirements:** Python 3.13, Node.js, MySQL, and `ffmpeg`
(`sudo apt install ffmpeg`).

```bash
# backend
cd ~/Projects/MediaBox/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# frontend
cd ../frontend
npm install
```

The database tables are created automatically the first time the API starts.

---

## Configuration

Two files, both already set up. Don't commit secrets into them.

**`backend/.env`**

```ini
MEDIA_DIR=/home/koeuk/Videos/video-download/medias   # where downloads are saved
DATABASE_URL=mysql+pymysql://root:...@127.0.0.1:3306/mediabox
```

**`frontend/.env`**

```ini
NUXT_PUBLIC_API_BASE=http://localhost:8005/api
```

`dev.sh` overrides `NUXT_PUBLIC_API_BASE` and `CORS_ORIGINS` at launch to match
the ports it actually bound. The value in `frontend/.env` only matters if you
start the servers by hand.

---

## Running the servers manually

If you'd rather not use the script — note these use fixed ports and will fail
if something else is already listening:

```bash
# terminal 1 — API
cd ~/Projects/MediaBox/backend
.venv/bin/python -m uvicorn app.main:app --reload --port 8005

# terminal 2 — web UI
cd ~/Projects/MediaBox/frontend
npm run dev -- --port 3005
```

What the API command means:

- `.venv/bin/python` — the project's virtualenv, which has the dependencies
- `-m uvicorn` — FastAPI is only a library; uvicorn is the server that listens
- `app.main:app` — the `app` object in `backend/app/main.py`
- `--reload` — restart on file save (development only)
- `--port 8005` — must match `NUXT_PUBLIC_API_BASE` in `frontend/.env`

Run the API from inside `backend/`. Started from the repo root, `--reload`
also watches `frontend/node_modules` and every restart crawls.

---

## Troubleshooting

**Downloads have a padlock / can't be deleted**
Files are root-owned from a `sudo` run. Fix with the `chown` above and never
start the servers as root.

**`port 8005 is already in use` when running manually**
A server from a previous session is still up. Find and stop it:

```bash
ss -ltnp | grep :8005
kill <pid>
```

`./dev.sh` handles this automatically by moving to the next free port.

**The UI loads but every request fails**
The API is down or on a different port. Check
http://localhost:8005/api/health — it should return
`{"status":"ok","app":"MediaBox"}`. If the API moved ports and you started
things manually, update `NUXT_PUBLIC_API_BASE` in `frontend/.env` to match.

**Browser console shows CORS errors**
The API only accepts the origin it was told about. `dev.sh` sets this
automatically; if running manually, set `CORS_ORIGINS` to your UI's URL:

```bash
CORS_ORIGINS=http://localhost:3005 .venv/bin/python -m uvicorn app.main:app --port 8005
```

**Ctrl-C leaves servers running**
Shouldn't happen with `dev.sh`. If it does, ports stay bound — find strays
with `ss -ltnp | grep -E ':(3005|8005)'` and kill them. Note the API waits for
in-flight downloads before shutting down, so it can take a couple of seconds.

**API won't start after a `git pull`**
New dependencies. Re-run `.venv/bin/pip install -r requirements.txt`.

---

## Docker (alternative)

`docker-compose.yml` runs everything in containers:

```bash
docker compose up
```

Be aware it stores media in a **named Docker volume**, not your
`~/Videos/video-download` folder — so it won't see your existing downloads.
