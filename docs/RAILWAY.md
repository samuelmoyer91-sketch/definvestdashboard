# Railway — how this project uses it

## The mental model

Three nested things:

- **Project** — the container. One.
- **Service** — a running app. One that matters: the triage app.
- **Deployment** — one build-and-run of one commit. A new deployment happens on
  every push to `main` **and** on every variable change.

The default project view is a **canvas**: each service is a rounded square on a
dotted grid, with lines drawn between linked services. It's an
architecture-diagram metaphor that pays off with five services; with one it
looks like a diagram of nothing. The square *is* the service — click it for the
tabs below.

## Where Railway sits in the stack

Three different deploy mechanisms, which is the main source of confusion:

| Piece | Runs on | Triggered by |
|---|---|---|
| Triage app (`src/web/`) | **Railway** | push to `main` — automatic |
| Public site (`github_site/`) | Cloudflare Pages | `gh workflow run publish.yml` — **not** push |
| Ingest / publish / export / migrate | GitHub Actions | cron + manual |
| Database | Turso | — |

**Pushing to `main` never updates capitalfordefense.com.** Railway and
Cloudflare are unrelated paths.

## The four tabs that matter

- **Deployments** — what's running, and history. Each entry is a commit. Also
  where you **roll back**: open an older successful deployment and redeploy it.
  Worth knowing before you need it.
- **Variables** — env vars and secrets. Changing anything here redeploys.
- **Logs** — the app's stdout/stderr. Where a 500 or a `logger.error` shows up.
  Filter to the newest deployment or you're reading history.
- **Settings** — domain, build command, restart policy. Rarely touched.

## Faster than the dashboard

```bash
curl -s https://capitalfordefense.up.railway.app/health | python3 -m json.tool
```

- `commit` — what is actually serving
- `uptime_s` — how long since the last deploy
- `env_configured` — which secrets the app has (booleans, never values)

Usually quicker than loading the UI for "did my push land".

⚠️ `/health` **deliberately does not touch the database**. It stayed green
through the schema outage while every real page 500'd. For a genuine check,
load `/master`.

## Gotchas specific to this project

- **Every deploy wipes in-memory state.** The `/health` accept timings live in
  a ring buffer in the process; any deploy — including a variable change —
  resets them to empty. Not a regression.
- **One database connection.** `StaticPool` gives the whole process a single
  libsql connection, so long operations block everything else, and background
  threads must never touch it while a request is in flight (commit `3fc8917`).
  This is why the roundup split re-extracts synchronously.
- **Builds come from `main` only.** Branch work deploys nothing until merged.
- **The app needs `ANTHROPIC_API_KEY`** as of 2026-08-08. It never did before —
  all extraction ran in Actions — so the variable was simply absent, and the
  roundup split silently produced blank cards. `/health`'s `env_configured`
  exists because of that.

## CLI

```bash
npm i -g @railway/cli
railway login
railway logs        # much nicer than the web log viewer
```
