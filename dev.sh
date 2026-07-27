#!/usr/bin/env bash
# Start MediaBox for local development: API + web UI together.
#
#   ./dev.sh                      API on :8005, web on :3005
#   API_PORT=9001 ./dev.sh        start looking from a different port
#
# Ports are starting points, not requirements: if one is taken the next free
# one is used, and the frontend is pointed at whichever port the API got.
# Ctrl-C stops both.
set -euo pipefail

cd "$(dirname "$0")"

API_PORT="${API_PORT:-8005}"
WEB_PORT="${WEB_PORT:-3005}"

die() { printf '\n\033[31merror:\033[0m %s\n\n' "$1" >&2; exit 1; }
note() { printf '\033[2m%s\033[0m\n' "$1"; }

# Running as root makes every downloaded file root-owned, which leaves the
# media folder undeletable from a file manager. This has bitten before.
if [ "$(id -u)" -eq 0 ]; then
  die "Do not run this with sudo.
  Downloads would be written as root and you could not delete them.
  Run it as your normal user instead."
fi

[ -x backend/.venv/bin/python ] \
  || die "backend/.venv is missing. Create it first:
  python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt"

[ -d frontend/node_modules ] \
  || die "frontend/node_modules is missing. Install first:
  cd frontend && npm install"

configured_media_dir="${MEDIA_DIR:-}"
if [ -z "$configured_media_dir" ] && [ -f backend/.env ]; then
  configured_media_dir=$(sed -n "s/^[[:space:]]*MEDIA_DIR[[:space:]]*=[[:space:]]*//p" backend/.env | tail -n 1)
  configured_media_dir="${configured_media_dir%%#*}"
  configured_media_dir="${configured_media_dir%\"}"
  configured_media_dir="${configured_media_dir#\"}"
fi
configured_media_dir="${configured_media_dir:-./media}"

case "$configured_media_dir" in
  "~") resolved_media_dir="$HOME" ;;
  "~/"*) resolved_media_dir="$HOME/${configured_media_dir#"~/"}" ;;
  /*) resolved_media_dir="$configured_media_dir" ;;
  *) resolved_media_dir="backend/$configured_media_dir" ;;
esac

case "$resolved_media_dir" in
  "/media/$(id -un)/"*)
    media_tail="${resolved_media_dir#"/media/$(id -un)/"}"
    media_mount="/media/$(id -un)/${media_tail%%/*}"
    [ -d "$media_mount" ] \
      || die "MEDIA_DIR drive is not mounted: $media_mount
  Mount it in Files, then run ./dev.sh again."
    ;;
esac

media_probe="$resolved_media_dir"
while [ ! -e "$media_probe" ] && [ "$media_probe" != "/" ]; do
  media_probe=$(dirname "$media_probe")
done

[ -d "$media_probe" ] && [ -w "$media_probe" ] \
  || die "MEDIA_DIR is not writable: $resolved_media_dir
  Mount the drive or edit backend/.env to use a writable folder."

mkdir -p "$resolved_media_dir" \
  || die "Could not create MEDIA_DIR: $resolved_media_dir"

[ -w "$resolved_media_dir" ] \
  || die "MEDIA_DIR exists but is not writable: $resolved_media_dir"

# A previous `sudo` run leaves build caches owned by root, and vite/nuxt then
# die with a bare EACCES deep in a stack trace. Catch it here instead.
for path in frontend/node_modules frontend/.nuxt "$resolved_media_dir" backend/mediabox.db; do
  [ -e "$path" ] || continue
  [ -w "$path" ] && [ -z "$(find "$path" -maxdepth 2 ! -user "$(id -un)" -print -quit 2>/dev/null)" ] \
    || die "$path contains files owned by another user (a previous sudo run).
  Fix it with:
  sudo chown -R $(id -un):$(id -gn) $PWD
  …and the same for your MEDIA_DIR from backend/.env"
done

port_busy() { ss -ltn 2>/dev/null | grep -q ":$1[[:space:]]"; }

# First free port at or above $1. Inherently racy — something could grab the
# port between the check and the bind — but the server then fails loudly, and
# for local dev that is a fair trade for not having to hunt down stale servers.
pick_port() {
  local port=$1 limit=$(($1 + 40))
  while [ "$port" -lt "$limit" ]; do
    port_busy "$port" || { printf '%s' "$port"; return 0; }
    port=$((port + 1))
  done
  return 1
}

api_wanted=$API_PORT
web_wanted=$WEB_PORT
API_PORT=$(pick_port "$api_wanted") || die "no free port near $api_wanted"
WEB_PORT=$(pick_port "$web_wanted") || die "no free port near $web_wanted"
[ "$API_PORT" = "$api_wanted" ] || note "port $api_wanted busy — API moved to $API_PORT"
[ "$WEB_PORT" = "$web_wanted" ] || note "port $web_wanted busy — web moved to $WEB_PORT"

# The browser reads this to reach the API, so it has to follow the port we
# actually bound. An exported value wins over frontend/.env, which dotenv
# will not use to overwrite an existing variable.
export NUXT_PUBLIC_API_BASE="http://localhost:$API_PORT/api"

# The API is a different origin from the page, so it must allow the port the
# UI actually got — otherwise every request fails CORS in the browser while
# curl still works, which is a miserable thing to debug.
export CORS_ORIGINS="http://localhost:$WEB_PORT,http://127.0.0.1:$WEB_PORT"

pids=()

# Kill a process and everything below it. Both servers spawn children —
# uvicorn's reloader forks a worker, npm forks nuxt which forks node — and
# signalling only the parent leaves those children holding the ports, so the
# next run silently shifts to different ports and talks to a stale server.
# Parent FIRST, then descendants. Nuxt's dev manager respawns its child
# whenever the child exits — that is how it restarts on a config change — so
# killing bottom-up makes it start a replacement on a new port before the
# manager itself is signalled. Take the supervisor down first and the
# children have nothing left to resurrect them.
# Every pid below $1, deepest last. `|| true` matters: pgrep exits 1 when a
# process has no children, and under `set -e` a bare assignment would abort
# cleanup before it ever reached the SIGKILL pass.
descendants() {
  local pid=$1 child kids
  kids=$(pgrep -P "$pid" 2>/dev/null) || true
  for child in $kids; do
    printf '%s ' "$child"
    descendants "$child"
  done
}

cleanup() {
  trap - EXIT INT TERM
  note ""
  note "stopping…"

  # Snapshot the whole tree BEFORE signalling anything. Killing a parent
  # reparents its children to init, and `pkill -P` can no longer find them —
  # that is how a stray nuxt node process used to survive holding the port.
  local targets=()
  local pid
  for pid in "${pids[@]}"; do
    # parent first, so nuxt's dev manager cannot respawn a replacement
    targets+=("$pid")
    # shellcheck disable=SC2207
    targets+=($(descendants "$pid"))
  done

  for pid in "${targets[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
  # uvicorn waits on in-flight downloads before it will exit, so don't wait
  # for a graceful stop forever — insist shortly after
  sleep 2
  for pid in "${targets[@]}"; do kill -KILL "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Run from backend/ so --reload watches only the API source — started from the
# repo root it also walks frontend/node_modules, which is tens of thousands of
# files and makes every restart crawl.
bash -c 'cd backend && exec .venv/bin/python -m uvicorn app.main:app --reload --port "$1"' _ "$API_PORT" &
pids+=($!)

npm --prefix frontend run dev -- --port "$WEB_PORT" &
pids+=($!)

printf '\n  \033[1mMediaBox\033[0m\n'
printf '  web  http://localhost:%s\n' "$WEB_PORT"
printf '  api  http://localhost:%s/api/health\n\n' "$API_PORT"
note "  Ctrl-C to stop both"

# exit as soon as either server dies, so a crashed backend doesn't go unnoticed
wait -n
