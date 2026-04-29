# Vantage Deployment Notes

Vantage is safe to run locally by default. Hosting it online needs a little extra care because the app can read and write Markdown state and can use an OpenAI API key.

## Recommended First Deployment

The supported V5 online shape is:

1. Run the app with Docker Compose.
2. Keep Vantage auth enabled.
3. Keep the container port bound to `127.0.0.1` unless you intentionally want direct LAN access.
4. Expose the app through Tailscale, Cloudflare Tunnel, Caddy, or another HTTPS reverse proxy.

Use a private tunnel or private network first:

- Tailscale: expose the running local server only to your own devices.
- Cloudflare Tunnel with Access: expose a private URL protected by Cloudflare login.
- Local network: bind to `0.0.0.0`, keep Vantage auth enabled, and visit `http://<your-computer-ip>:8005` from another device on the same Wi-Fi.

For any internet-reachable deployment, also set Vantage's built-in Basic Auth password.

The server now refuses to listen on a non-local host without auth unless
`VANTAGE_V5_ALLOW_UNSAFE_PUBLIC_NO_AUTH=true` is explicitly set. Treat that override
as a temporary private-network escape hatch, not an internet setting.

## Environment

```bash
OPENAI_API_KEY=sk-...
VANTAGE_V5_MODEL=gpt-4.1
VANTAGE_V5_HOST=0.0.0.0
VANTAGE_V5_PORT=8005
VANTAGE_V5_PUBLISH_HOST=127.0.0.1
VANTAGE_V5_REPO_ROOT=/data
VANTAGE_V5_CANONICAL_ROOT=
VANTAGE_V5_ACTIVE_WORKSPACE=v5-milestone-1
VANTAGE_V5_AUTH_USERNAME=vantage
VANTAGE_V5_AUTH_PASSWORD=replace-with-a-long-random-password
VANTAGE_V5_ALLOWED_HOSTS=
VANTAGE_V5_ALLOWED_ORIGINS=
VANTAGE_V5_COOKIE_SECURE=false
VANTAGE_V5_ALLOW_UNSAFE_PUBLIC_NO_AUTH=false
# Optional multi-user profile mode:
# VANTAGE_V5_AUTH_USERS_JSON={"eden":"long-password-1","jordan":"long-password-2"}
# VANTAGE_V5_AUTH_USERS_FILE=/data/users.json
```

Notes:

- `VANTAGE_V5_HOST` defaults to `127.0.0.1` for local-only development. Use `0.0.0.0` only inside a container, VM, private network, or reverse-proxy deployment.
- `VANTAGE_V5_PUBLISH_HOST` is used by `compose.yaml`, not by the Python app. Keep it as `127.0.0.1` when Caddy, Cloudflare Tunnel, or Tailscale Serve runs on the same machine. Set it to `0.0.0.0` only when another computer should connect directly to the port.
- `VANTAGE_V5_AUTH_PASSWORD` enables the Vantage sign-in screen for the configured `VANTAGE_V5_AUTH_USERNAME`; API clients may still use HTTP Basic Auth with the same credentials.
- `VANTAGE_V5_AUTH_USERS_JSON` or `VANTAGE_V5_AUTH_USERS_FILE` enables multi-user profile mode. Each username signs in to its own isolated Markdown store under `users/<username>/`.
- Keep using long random passwords. The JSON values are plaintext deployment secrets and should be supplied through your host secret manager or an uncommitted file.
- `VANTAGE_V5_ALLOWED_HOSTS` is optional but recommended behind a domain. Example: `vantage.example.com,localhost,127.0.0.1`.
- `VANTAGE_V5_ALLOWED_ORIGINS` is optional and useful behind HTTPS. Example: `https://vantage.example.com`.
- `VANTAGE_V5_COOKIE_SECURE=true` should be used when browsers reach Vantage over HTTPS through a reverse proxy or tunnel.
- `/api/health` stays unauthenticated so hosts and reverse proxies can perform uptime checks.
- `VANTAGE_V5_REPO_ROOT` controls where Vantage stores Markdown state. In Docker, use `/data` and mount it as persistent storage.
- `VANTAGE_V5_CANONICAL_ROOT` usually stays blank. Docker reads shipped canonical defaults from the image; source checkouts read them from `canonical/`.

## Easiest Online Paths

### Same Wi-Fi or Tailscale

This is the lowest-friction route for trying Vantage from another computer.

```bash
cp .env.online.example .env.online
# Edit .env.online and set a long VANTAGE_V5_AUTH_PASSWORD.
docker compose --env-file .env.online up --build
```

Then open one of these from the other computer:

- Same Wi-Fi direct port: set `VANTAGE_V5_PUBLISH_HOST=0.0.0.0`, then open `http://<this-computer-lan-ip>:8005`.
- Tailscale direct port: set `VANTAGE_V5_PUBLISH_HOST=0.0.0.0`, then open `http://<this-computer-tailscale-name-or-ip>:8005`.
- Tailscale Serve: keep `VANTAGE_V5_PUBLISH_HOST=127.0.0.1` and let Tailscale forward to `http://127.0.0.1:8005`.

### Public Domain With HTTPS

For a real public URL, put Vantage behind a reverse proxy such as Caddy, Cloudflare Tunnel, Tailscale Funnel, or a hosted platform proxy.

Use these settings:

```bash
VANTAGE_V5_HOST=0.0.0.0
VANTAGE_V5_PUBLISH_HOST=127.0.0.1
VANTAGE_V5_AUTH_PASSWORD=replace-with-a-long-random-password
VANTAGE_V5_ALLOWED_HOSTS=vantage.example.com,localhost,127.0.0.1
VANTAGE_V5_ALLOWED_ORIGINS=https://vantage.example.com
VANTAGE_V5_COOKIE_SECURE=true
```

A starter Caddy reverse-proxy file lives at `deploy/Caddyfile.example`.
A starter Cloudflare Tunnel config lives at `deploy/cloudflared-config.example.yml`.

### Cloudflare Tunnel

Use this when you want a public URL without opening an inbound port on your router or cloud firewall.

1. Start Vantage with Compose and keep `VANTAGE_V5_PUBLISH_HOST=127.0.0.1`.
2. Point the tunnel service at `http://127.0.0.1:8005`.
3. Set `VANTAGE_V5_ALLOWED_HOSTS` to the public hostname.
4. Set `VANTAGE_V5_ALLOWED_ORIGINS` to the public `https://` origin.
5. Set `VANTAGE_V5_COOKIE_SECURE=true`.
6. If you want the URL private, enable Cloudflare Access in front of it as an additional identity layer.

### Caddy Reverse Proxy

Use this when the machine has a domain pointed at it and can receive public HTTP/HTTPS traffic.

1. Start Vantage with Compose and keep `VANTAGE_V5_PUBLISH_HOST=127.0.0.1`.
2. Copy `deploy/Caddyfile.example` into your Caddy config.
3. Replace `vantage.example.com` with your domain.
4. Set `VANTAGE_V5_ALLOWED_HOSTS`, `VANTAGE_V5_ALLOWED_ORIGINS`, and `VANTAGE_V5_COOKIE_SECURE=true` in `.env.online`.

## Persistent Storage

Back up and persist these directories together:

```text
artifacts/
concepts/
memories/
memory_trace/
state/
traces/
users/
workspaces/
```

These directories are the product database today. Losing them loses saved whiteboards, artifacts, memories, experiment state, and trace history.

When auth is enabled, each user has the same directory layout under `users/<username>/`. Back up the whole `users/` directory as part of the persistent data volume.

## Docker

Build:

```bash
docker build -t vantage-v5 .
```

Run with a named volume:

```bash
docker volume create vantage-v5-data

docker run --rm \
  --name vantage-v5 \
  -p 127.0.0.1:8005:8005 \
  -v vantage-v5-data:/data \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e VANTAGE_V5_AUTH_USERNAME="vantage" \
  -e VANTAGE_V5_AUTH_PASSWORD="replace-with-a-long-random-password" \
  vantage-v5
```

The container entrypoint initializes an empty `/data` volume with the required directories, `state/active_workspace.json`, and a starter whiteboard if they do not already exist.

Or use Compose:

```bash
cp .env.online.example .env.online
# edit .env.online first
docker compose --env-file .env.online up --build -d
```

## Reverse Proxy

If you put Vantage behind Caddy, Nginx, Cloudflare, or Tailscale Serve:

- Terminate HTTPS at the proxy.
- Keep `VANTAGE_V5_AUTH_PASSWORD` set unless the proxy enforces stronger identity.
- Set `VANTAGE_V5_COOKIE_SECURE=true` when browsers access the site over HTTPS.
- Set `VANTAGE_V5_ALLOWED_HOSTS` and `VANTAGE_V5_ALLOWED_ORIGINS` to the public domain.
- Do not forward the app without authentication to the public internet.
- Mount or back up the persistent storage directories before upgrading containers.

## Current Limits

- Auth is still HTTP Basic Auth, but it can now map separate usernames to isolated private Markdown profiles.
- Multi-user mode is profile isolation, not team collaboration. There are no shared workspaces, invites, roles, or simultaneous editing semantics yet.
- File-backed Markdown state is best for private/personal profiles, not concurrent collaborative editing.
- There is no built-in backup scheduler yet.
