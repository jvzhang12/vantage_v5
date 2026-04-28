# Vantage Deployment Notes

Vantage is safe to run locally by default. Hosting it online needs a little extra care because the app can read and write Markdown state and can use an OpenAI API key.

## Recommended First Deployment

Use a private tunnel or private network first:

- Tailscale: expose the running local server only to your own devices.
- Cloudflare Tunnel with Access: expose a private URL protected by Cloudflare login.

For any internet-reachable deployment, also set Vantage's built-in Basic Auth password.

## Environment

```bash
OPENAI_API_KEY=sk-...
VANTAGE_V5_MODEL=gpt-4.1
VANTAGE_V5_HOST=0.0.0.0
VANTAGE_V5_PORT=8005
VANTAGE_V5_REPO_ROOT=/data
VANTAGE_V5_ACTIVE_WORKSPACE=v5-milestone-1
VANTAGE_V5_AUTH_USERNAME=vantage
VANTAGE_V5_AUTH_PASSWORD=replace-with-a-long-random-password
# Optional multi-user profile mode:
# VANTAGE_V5_AUTH_USERS_JSON={"eden":"long-password-1","jordan":"long-password-2"}
# VANTAGE_V5_AUTH_USERS_FILE=/data/users.json
```

Notes:

- `VANTAGE_V5_HOST` defaults to `127.0.0.1` for local-only development. Use `0.0.0.0` only inside a container, VM, private network, or reverse-proxy deployment.
- `VANTAGE_V5_AUTH_PASSWORD` enables HTTP Basic Auth for the UI and API. If it is empty, auth is disabled for local development.
- `VANTAGE_V5_AUTH_USERS_JSON` or `VANTAGE_V5_AUTH_USERS_FILE` enables private multi-user profile mode. The Basic Auth username selects an isolated Markdown store under `users/<username>/`.
- If multi-user profile mode is enabled, keep using long random passwords. The JSON values are plaintext deployment secrets and should be supplied through your host secret manager or an uncommitted file.
- `/api/health` stays unauthenticated so hosts and reverse proxies can perform uptime checks.
- `VANTAGE_V5_REPO_ROOT` controls where Vantage stores Markdown state. In Docker, use `/data` and mount it as persistent storage.

## Persistent Storage

Back up and persist these directories together:

```text
artifacts/
concepts/
memories/
memory_trace/
state/
traces/
workspaces/
```

These directories are the product database today. Losing them loses saved whiteboards, artifacts, memories, experiment state, and trace history.

In multi-user profile mode, each user has the same directory layout under `users/<username>/`. Back up the whole `users/` directory as part of the persistent data volume.

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
  -p 8005:8005 \
  -v vantage-v5-data:/data \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e VANTAGE_V5_AUTH_USERNAME="vantage" \
  -e VANTAGE_V5_AUTH_PASSWORD="replace-with-a-long-random-password" \
  vantage-v5
```

The container entrypoint initializes an empty `/data` volume with the required directories, `state/active_workspace.json`, and a starter whiteboard if they do not already exist.

## Reverse Proxy

If you put Vantage behind Caddy, Nginx, Cloudflare, or Tailscale Serve:

- Terminate HTTPS at the proxy.
- Keep `VANTAGE_V5_AUTH_PASSWORD` set unless the proxy enforces stronger identity.
- Do not forward the app without authentication to the public internet.
- Mount or back up the persistent storage directories before upgrading containers.

## Current Limits

- Auth is still HTTP Basic Auth, but it can now map separate usernames to isolated private Markdown profiles.
- Multi-user mode is profile isolation, not team collaboration. There are no shared workspaces, invites, roles, or simultaneous editing semantics yet.
- File-backed Markdown state is best for private/personal profiles, not concurrent collaborative editing.
- There is no built-in backup scheduler yet.
