# Production: droplinks.site

The production stack serves **https://droplinks.site**, proxies `/api` and
WebSockets to FastAPI, and sends password reset links to this public URL.
Caddy manages HTTPS and certificate renewal. MySQL, FastAPI, and Nuxt are only
reachable on the Compose network; Caddy publishes ports 80 and 443.

## Configuration

Use the project root on the server. Copy `.env.production.example` to
`.env.production` if the latter is missing, then restrict access:

```bash
chmod 600 .env.production
```

Set these values in `.env.production`:

| Variable | Value |
| --- | --- |
| `DOMAIN` | `droplinks.site` (hostname only) |
| `SECRET_KEY` | Existing production JWT secret, or a new random secret for a fresh installation |
| `DB_PASSWORD` | Existing production MySQL root password, or a new random password for a fresh installation |
| `SMTP_USERNAME` | Your Gmail address |
| `SMTP_FROM_EMAIL` | The same Gmail address |
| `SMTP_PASSWORD` | Your Google App Password, without spaces |

For a **fresh** installation, generate each secret separately:

```bash
openssl rand -hex 32
```

For an **existing** installation, keep its current `DB_PASSWORD` and
`SECRET_KEY`. Changing the MySQL environment value does not change the password
inside an existing database volume. Keep the same Compose project name and
project directory so the existing `mysql_data` and `media_data` volumes are used.
If your deployment used `-p`, pass that same `-p` value to every command below.
Do not use `down -v`, which deletes data volumes.

`DB_PASSWORD` is supplied separately to SQLAlchemy, so special URL characters
in the password do not need encoding. Single-quote dotenv values containing
`$`, `#`, or spaces. Do not commit `.env.production`; it is ignored by Git and
excluded from image build contexts. This file is distinct from the developer
settings in `backend/.env` and `frontend/.env`.

Gmail requires [2-Step Verification and an App Password](https://support.google.com/accounts/answer/185833).
The template uses `smtp.gmail.com`, port 587, with STARTTLS. Keep the normal
Google account password out of this configuration.

The production Compose file sets:

- `FRONTEND_URL=https://droplinks.site` and matching CORS origin.
- Browser API URL `/api` and secure authentication cookies.
- Gmail settings from `.env.production`; reset links expire after 30 minutes.
- Private-network download targets disabled.
- Persistent media, database, and TLS-certificate volumes.

## DNS and HTTPS

Point the domain's DNS A record to the server's public IPv4 address. Add an AAAA
record only when that server also handles public IPv6. Allow inbound TCP 80
and 443. Caddy must be able to bind these ports; if another host-level web
server already uses them, integrate with that proxy instead of starting a
second proxy on the same ports.

Once DNS reaches this server, Caddy issues and renews the certificate and
redirects HTTP to HTTPS. The HTTPS stack is designed for direct domain-to-server
traffic; a separately managed CDN or existing HTTPS proxy may need its own
origin settings.

## Validate and start

Install Docker Engine and the Docker Compose plugin on the server. Validate
without printing resolved secrets:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
```

Then start or update the production stack:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build --remove-orphans
```

When updating the older Compose stack in the same project, `--remove-orphans`
removes its old nginx container as Caddy takes over. Named database/media
volumes are retained. Database migrations run automatically on backend startup.

Check services and API:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml ps
curl --fail https://droplinks.site/api/health
```

From a checkout with Node.js installed, verify the public deployment:

```bash
npm --prefix frontend run check:production -- https://droplinks.site
```

This checks the login page for Nuxt development assets, checks for an accidental
localhost API URL, and verifies `/api/health`. An unreachable host fails the
check rather than reporting a successful deployment.

If DevTools shows `/@vite/client`, `/_nuxt/@fs/`, `virtual:nuxt`, or hundreds of
individual source modules, check the frontend process and reverse-proxy target.
The Docker image already builds the app and runs its production server. Outside
Docker, run `npm ci` and `npm run build` in `frontend/`, then configure the process
manager to run `npm start` with `NODE_ENV=production`, `NUXT_PUBLIC_API_BASE=/api`,
and `NUXT_PUBLIC_COOKIE_SECURE=true`. Point the reverse proxy at that server's
port. `npm run dev` and `bash dev.sh` are for local development.

Check backend and HTTPS logs when troubleshooting:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=100 backend caddy
```

Avoid sharing full `docker compose config` output: it contains environment
secrets. Use `config --quiet` for validation.

## Gmail verification

After filling the credentials and starting the backend, open
`https://droplinks.site/forgot-password` and request a link for an account you
own. The email should point to `https://droplinks.site/reset-password#token=…`.
Use the link once to choose a new password, then sign in again. A successful
reset invalidates previous sessions. No real email is sent by the automated
test suite; SMTP delivery is mocked.

If SMTP is not configured, the form reports that email recovery is unavailable.
If delivery fails, backend logs record the failure without addresses, reset
links, or passwords. The request response stays generic so it does not reveal
which addresses have accounts.
