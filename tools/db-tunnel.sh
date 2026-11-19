#!/usr/bin/env bash
# Forward a local port to MySQL on the SSH server's loopback interface.
set -euo pipefail

ssh_host="${1:?Usage: bash tools/db-tunnel.sh user@server local-port}"
local_port="${2:?A local MySQL port is required}"
[[ "$local_port" =~ ^[0-9]+$ ]] && (( local_port > 0 && local_port < 65536 )) \
  || { printf 'Invalid database tunnel port\n' >&2; exit 1; }

control_dir="${XDG_CACHE_HOME:-$HOME/.cache}/mediabox"
mkdir -p "$control_dir"
control_socket="$control_dir/mysql-%C-$local_port.sock"

if ssh -S "$control_socket" -O check "$ssh_host" >/dev/null 2>&1; then
  printf 'MySQL SSH tunnel already running on 127.0.0.1:%s\n' "$local_port"
  exit 0
fi

ssh -fNT -M -S "$control_socket" \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  -o ConnectTimeout=10 \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L "127.0.0.1:$local_port:127.0.0.1:3306" "$ssh_host"
printf 'MySQL SSH tunnel opened on 127.0.0.1:%s\n' "$local_port"
