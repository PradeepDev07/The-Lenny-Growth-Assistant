# Vercel Deployment Guide — The Lenny Growth Assistant (DEPLOY_VERCEL.md)

> **Document Purpose:** Complete operational guide for deploying **The Lenny Growth Assistant** frontend studio to Vercel via **Native Vercel Next.js** or **Custom Standalone Docker (`Dockerfile.vercel`)**.

---

## 1. Executive Summary & Deployment Architecture

The Lenny Growth Assistant architecture decouples the Next.js 14 frontend studio from the FastAPI backend service:

```text
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT BROWSER                            │
│           https://lennygrowth.pradeepleadsystems.in          │
└───────────────────────────────┬──────────────────────────────┘
                                │
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        ▼ (Page loads & Static assets)                  ▼ (API calls & SSE Streams)
┌────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│     VERCEL / CONTAINER RUNTIME         │     │            FASTAPI BACKEND             │
│   • Next.js 14 Standalone Server       │     │   • Domain: lennygrowthapi...          │
│   • https://lennygrowth...             │     │   • TaskRouter & Hybrid RAG (BM25)     │
│   • Port: $PORT (binds to 0.0.0.0)     │     │   • Model Providers (Gemini / Ollama)  │
│   • Dockerfile.vercel / vercel.json    │     │   • PostgreSQL / SQLite Persistence    │
└────────────────────────────────────────┘     └────────────────────────────────────────┘
```

The frontend can be deployed via:
1. **Native Vercel Deployment**: Using `vercel.json` and Vercel's zero-config Next.js runtime.
2. **Containerized Standalone Deployment**: Using `Dockerfile.vercel` for container runtimes, self-hosted environments, or cloud container platforms.

---

## 2. Configuration & Environment Variables

### Environment Variables Matrix

| Variable | Scope | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | **Build & Runtime** | `https://thelennygrowthassistant-backend-latest.onrender.com` | Base URL of the FastAPI backend. **Must be provided at build time** for client-side JavaScript inlining. |
| `PORT` | **Runtime** | `3000` | Port on which the standalone server listens. Automatically overridden by container orchestrators. |
| `HOSTNAME` | **Runtime** | `0.0.0.0` | Network interface to bind. Must be `0.0.0.0` so ingress traffic reaches the container. |
| `NODE_ENV` | **Build & Runtime** | `production` | Optimizes React and Next.js for production execution. |
| `NEXT_TELEMETRY_DISABLED` | **Build & Runtime** | `1` | Disables telemetry reporting during builds and execution. |

> [!IMPORTANT]
> **Build-Time Inlining:** Next.js bakes `NEXT_PUBLIC_*` variables into client-side JS bundles during `npm run build`. If building via Docker, pass `--build-arg NEXT_PUBLIC_API_URL="https://thelennygrowthassistant-backend-latest.onrender.com"`.

---

## 3. Option A: Native Vercel Deployment

### Method 1: Git Integration (Recommended)
1. Push your repository to GitHub / GitLab / Bitbucket.
2. Log into the [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New Project"**.
3. Import the repository.
4. Configure project settings:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (or default)
   - **Output Directory:** Default / Override OFF (automatically `.next`; **do NOT override to `frontend/.next`**)
   - **Install Command:** `npm ci --include=dev` (configured in `frontend/vercel.json`)
5. In **Environment Variables**, add:
   ```text
   NEXT_PUBLIC_API_URL = https://thelennygrowthassistant-backend-latest.onrender.com
   ```
6. Click **Deploy**.

### Method 2: Vercel CLI
Deploy directly from your terminal using Vercel CLI:
```bash
# Install Vercel CLI if not present
npm i -g vercel

# From frontend directory
cd frontend
vercel link
vercel env add NEXT_PUBLIC_API_URL production
vercel --prod
```

### Vercel Rewrites & Security Headers (`frontend/vercel.json`)
`frontend/vercel.json` provides API proxying and security headers:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "installCommand": "npm ci --include=dev",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "SAMEORIGIN" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ],
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://thelennygrowthassistant-backend-latest.onrender.com/api/:path*" },
    { "source": "/health", "destination": "https://thelennygrowthassistant-backend-latest.onrender.com/health" },
    { "source": "/config", "destination": "https://thelennygrowthassistant-backend-latest.onrender.com/config" }
  ]
}
```

---

## 4. Option B: Standalone Docker Deployment (`Dockerfile.vercel`)

For container platforms, private clouds, or self-hosted container runtimes:

### 1. Build from Repository Root
```bash
docker build \
  -f Dockerfile.vercel \
  --build-arg NEXT_PUBLIC_API_URL="https://thelennygrowthassistant-backend-latest.onrender.com" \
  -t frontend-vercel .
```

### 2. Build from Frontend Directory
```bash
cd frontend
docker build \
  -f Dockerfile.vercel \
  --build-arg NEXT_PUBLIC_API_URL="https://thelennygrowthassistant-backend-latest.onrender.com" \
  -t frontend-vercel .
```

### 3. Run and Validate Container
```bash
# Run container with dynamic port injection and 0.0.0.0 interface binding
docker run --rm -d \
  --name lenny-frontend-prod \
  -p 3000:3000 \
  -e PORT=3000 \
  -e HOSTNAME="0.0.0.0" \
  frontend-vercel

# Test HTTP response
curl -I http://localhost:3000

# Inspect server logs
docker logs -f lenny-frontend-prod

# Stop container
docker stop lenny-frontend-prod
```

---

## 5. Dockerfile Architecture Highlights

`Dockerfile.vercel` uses a 3-stage minimal footprint build:

1. **`deps` Stage (`node:20-alpine`):**
   - Installs `libc6-compat` for Alpine Linux.
   - Copies `package.json` and `package-lock.json`.
   - Runs `npm ci || npm install` for reliable cross-platform dependency resolution.

2. **`builder` Stage (`node:20-alpine`):**
   - Ingests `NEXT_PUBLIC_API_URL` as a build argument (`ARG`).
   - Copies application source code and runs `npm run build`.
   - Emits optimized standalone bundle via `output: "standalone"` in `next.config.mjs`.

3. **`runner` Stage (`node:20-alpine`):**
   - Operates as unprivileged user `nextjs:nodejs` (UID/GID 1001) for strict container security.
   - Sets `HOSTNAME="0.0.0.0"` and `PORT=3000` (respects cloud-injected `$PORT`).
   - Copies only standalone artifacts, static chunks (`.next/static`), and public assets (`public/`).
   - Starts directly with `CMD ["node", "server.js"]` without heavy package manager overhead.

---

## 6. Verification Checklist

| Check | Command | Expected Result |
| :--- | :--- | :--- |
| **Lint Check** | `cd frontend && npm run lint` | `✔ No ESLint warnings or errors` |
| **Next.js Build** | `cd frontend && npm run build` | `✓ Generating static pages (5/5)` & standalone output |
| **Local Standalone Run** | `cd frontend && npm run start:standalone` | Server starts on `0.0.0.0:3000` |
| **Docker Build** | `docker build -f Dockerfile.vercel -t frontend-vercel-test .` | Successful build (code 0) |
| **Docker Compose Build** | `docker compose build` | Both `frontend` and `backend` built successfully |
| **Container Dynamic Port** | `docker run --rm -d -p 3030:3030 -e PORT=3030 frontend-vercel-test` | `curl -I http://localhost:3030` returns `HTTP/1.1 200 OK` |
| **Non-root Security** | `docker exec <container-id> id` | `uid=1001(nextjs) gid=1001(nodejs)` |

---

## 7. Troubleshooting & Common Pitfalls

### Pitfall 1: `npm ci` fails with `code EUSAGE` during Docker build
- **Root Cause:** `package.json` and `package-lock.json` were out of sync due to missing optional or peer dependencies (`@emnapi/core`, `@emnapi/runtime`).
- **Resolution:** Added `@emnapi/core` and `@emnapi/runtime` to `devDependencies` and synchronized `package-lock.json`.

### Pitfall 2: Client bundle connects to `http://localhost:8000` in production
- **Root Cause:** Next.js replaces `process.env.NEXT_PUBLIC_API_URL` during the `npm run build` step. If not passed during the Docker build, it falls back to localhost.
- **Resolution:** Pass `--build-arg NEXT_PUBLIC_API_URL="https://your-backend-domain.com"` during `docker build`.

### Pitfall 3: Container unhealthy or inaccessible externally
- **Root Cause:** Server bound to `127.0.0.1` (localhost loopback) instead of `0.0.0.0`.
- **Resolution:** `Dockerfile.vercel` explicitly sets `ENV HOSTNAME="0.0.0.0"`.

### Pitfall 4: Iframe preview fails with `Refused to display in a frame`
- **Root Cause:** Content Security Policy `frame-ancestors` directive on backend `/api/skills/preview` blocks the domain.
- **Resolution:** Backend `backend/app/routers/skills.py` is configured with `frame-ancestors 'self' https://lennygrowth.pradeepleadsystems.in;`. Add your Vercel deployment domain to `ALLOWED_ORIGINS` in backend configuration.
