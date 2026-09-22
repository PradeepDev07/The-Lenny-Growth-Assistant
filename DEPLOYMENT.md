# The Lenny Growth Assistant — Production Deployment Guide (DEPLOYMENT.md)

> **Document Purpose:** Complete operational reference for deploying, configuring, maintaining, and troubleshooting **The Lenny Growth Assistant** in production environments.

---

## 1. Production Architecture

The production architecture separates the Next.js frontend, FastAPI backend gateway, and persistence layer into decoupled services communicating over HTTPS and internal container networks:

```text
┌────────────────────────────────────────────────────────┐
│ PUBLIC INTERNET / CLIENT BROWSER                       │
│ URL: https://lennygrowth.pradeepleadsystems.in         │
└───────────────────────────┬────────────────────────────┘
                            │ HTTPS (Port 443)
                            ▼
┌────────────────────────────────────────────────────────┐
│ REVERSE PROXY / SSL TERMINATION (Nginx / Cloudflare)    │
│ • Handles SSL/TLS termination with Let's Encrypt       │
│ • Routes / to Next.js Frontend (:3000)                 │
│ • Routes /api/*, /health, /config to FastAPI (:8000)   │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│ NEXT.JS 14 FRONTEND RUNNER    │ │ FASTAPI BACKEND GATEWAY       │
│ • Standalone Node.js server   │ │ • Uvicorn ASGI runner (:8000) │
│ • Non-root nodejs user        │ │ • Multi-provider TaskRouter   │
│ • SSR & Static Asset Delivery │ │ • Boosted BM25 Vector Store   │
└───────────────────────────────┘ └──────────────┬────────────────┘
                                                 │
                                                 ▼
                                  ┌───────────────────────────────┐
                                  │ POSTGRESQL / SQLITE STORAGE   │
                                  │ • Sessions, Messages,         │
                                  │   Artifacts, Routing Logs     │
                                  │ • Automatic table migrations  │
                                  └───────────────────────────────┘
```

---

## 2. Services Breakdown

| Service | Technology | Runtime Role | Production Port |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js 14 (App Router, Standalone) | Serves the Light Liquid Glass UI, handles split-pane rendering, consumes SSE stream. | 3000 |
| **Backend API** | FastAPI (Python 3.12, Uvicorn) | API Gateway, RAG prompt compiler, session management, and SSE streaming coordinator. | 8000 |
| **Database** | PostgreSQL 16 (or SQLite) | Relational storage for sessions, message threads, artifacts, and routing telemetry. | 5432 |
| **Vector / Retrieval** | In-Memory / Cached BM25 | Field-boosted lexical search over pre-chunked transcript cache (`vector_cache.json`). | Embedded |
| **Cloud LLM Providers** | Google Gemini & OpenRouter | High-throughput cloud inference for RAG Q&A, long-form essays, and code synthesis. | Outbound HTTPS |
| **Local LLM (Dev)** | Ollama (`llama3.2:3b`) | Offline fallback and local developer testing on Apple Silicon Metal acceleration. | 11434 (Host) |

---

## 3. Environment Variables Specification

> **SECURITY NOTE:** Never commit actual secret keys or credentials to version control. Set these variables in your hosting provider's secrets manager or local `.env` file.

### Backend Environment Variables:
```env
# Application Metadata
ENVIRONMENT=production
LOG_LEVEL=INFO
APP_VERSION=1.0.0

# CORS & Networking
CORS_ORIGINS=https://lennygrowth.pradeepleadsystems.in,http://localhost:3000

# Database Persistence
# Production Postgres: postgresql+asyncpg://user:password@host:5432/dbname
# Local SQLite fallback: sqlite+aiosqlite:///./growth_assistant.db
DATABASE_URL=

# Local Ollama Configuration (Optional in production when cloud keys are present)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b

# Cloud LLM Credentials
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

OPENROUTER_API_KEY=
OPENROUTER_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free

# Model Router Task Defaults
MODEL_FOR_INTENT=gemini-2.5-flash-lite
MODEL_FOR_RETRIEVAL_QA=gemini-2.5-flash
MODEL_FOR_ESSAY=nvidia/nemotron-3-ultra-550b-a55b:free
MODEL_FOR_ARTIFACT=gemini-2.5-flash
```

### Frontend Environment Variables:
```env
# Backend API Base URL
NEXT_PUBLIC_API_URL=https://api.lennygrowth.pradeepleadsystems.in
```
*(If frontend and backend are served behind the same reverse proxy domain, `NEXT_PUBLIC_API_URL` can be left as an empty string or relative path `/api`)*.

---

## 4. Local Development Setup

### Prerequisites:
- Python 3.12+
- Node.js 20+
- (Optional) Ollama with `llama3.2:3b` installed (`ollama pull llama3.2:3b`)

### Step 1: Clone Repository & Install Backend
```bash
git clone https://github.com/PradeepDev07/The-Lenny-Growth-Assistant.git
cd "The-Lenny-Growth-Assistant"

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r backend/requirements.txt
```

### Step 2: Ingest Podcast Transcripts
```bash
# Indexes all transcripts from ingestion/data into vector_cache.json
python -m ingestion.ingest --refresh
```

### Step 3: Run Backend Development Server
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Run Frontend Development Server
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 5. Production Docker Compose Deployment

The entire stack can be launched in a single command using the root `docker-compose.yml`:

```bash
# 1. Populate your .env file with your cloud API keys:
echo "GEMINI_API_KEY=your_gemini_key" >> .env
echo "OPENROUTER_API_KEY=your_openrouter_key" >> .env

# 2. Build and run all containerized services:
docker compose up -d --build

# 3. View live service logs:
docker compose logs -f
```

### Service Health Checks:
- Backend: `curl -f http://localhost:8000/health`
- Database: `docker exec -it lenny-db pg_isready -U postgres`
- Frontend: `curl -I http://localhost:3000`

---

## 6. Database Setup & Migrations

The application manages database table creation automatically on startup via SQLAlchemy ORM lifespan hooks (`backend/app/main.py`):
1. When the backend container boots, `init_db()` executes `Base.metadata.create_all`.
2. Tables created:
   - `sessions`: Conversation threads and user metadata.
   - `messages`: User prompts, assistant streaming outputs, and source citations.
   - `artifacts`: Generated Markdown essays and sandboxed HTML applications.
   - `routing_logs`: Model routing, latency telemetry, and fallback logs.
3. For SQLite: `PRAGMA foreign_keys = ON` is executed on every connection to enforce cascade deletions.
4. For PostgreSQL: Native foreign key constraints with `ON DELETE CASCADE` handle atomic cleanup.

---

## 7. Transcript Ingestion & Index Maintenance

The knowledge base is built from structured transcript files located in `ingestion/data/`:
- `brian_balfour_growth_loops.json`
- `elena_verna_plg_activation.json`
- `shreyas_doshi_pm_metrics.json`
- `lenny_rachitsky_pmf_0_to_1.json`

### To add new podcast episodes:
1. Save the new transcript JSON file inside `ingestion/data/` conforming to the schema:
   ```json
   {
     "episode_id": "episode-slug",
     "title": "Episode Title",
     "guest": "Guest Name",
     "url": "https://www.lennyspodcast.com/episode-slug",
     "transcript": "Full text transcript..."
   }
   ```
2. Run the ingestion command:
   ```bash
   python -m ingestion.ingest --refresh
   ```
3. Commit and redeploy the updated `vector_cache.json`.

---

## 8. Custom Domain & DNS Configuration

To route traffic to **`https://lennygrowth.pradeepleadsystems.in`**:

1. Log into your DNS provider (e.g. GoDaddy / `domaincontrol.com`).
2. Add a new **CNAME** or **A** record:
   - **Type:** `CNAME`
   - **Name (Host):** `lennygrowth`
   - **Value / Target:** Your hosting server domain or ingress IP (e.g. `cname.vercel-dns.com` or server public IP).
   - **TTL:** 300 seconds (or automatic).
3. SSL Certificate:
   - Automatically provisioned via Vercel, Cloudflare, or Let's Encrypt Certbot:
     ```bash
     certbot --nginx -d lennygrowth.pradeepleadsystems.in
     ```
4. Update `CORS_ORIGINS` in backend configuration:
   ```env
   CORS_ORIGINS=https://lennygrowth.pradeepleadsystems.in
   ```

---

## 9. Security Audit & Hardening

Before deploying to production, verify the following:
1. **No API Keys in Frontend Bundle:** Inspect built JS bundles (`grep -rn "AIza" frontend/.next/`) to confirm no secret keys are leaked client-side. All LLM calls must originate server-side.
2. **Iframe Content-Security-Policy:** Ensure `skills.py` authorizes the production domain in `frame-ancestors`:
   ```text
   frame-ancestors 'self' https://lennygrowth.pradeepleadsystems.in;
   ```
3. **CORS Validation:** Test from a third-party origin to ensure cross-origin requests from untrusted domains are rejected.
4. **Environment Isolation:** Verify `.env` is listed in `.gitignore` and never committed to Git.

---

## 10. Troubleshooting & Common Issues

### Issue 1: Iframe preview fails to load with "Refused to display in a frame"
- **Root Cause:** Content-Security-Policy `frame-ancestors` directive does not include the host domain.
- **Fix:** Add `https://lennygrowth.pradeepleadsystems.in` to the CSP header in `backend/app/routers/skills.py`.

### Issue 2: Backend logs `httpx.ConnectError` to `localhost:11434` in Docker
- **Root Cause:** A container's `localhost` loopback cannot see services on the host machine.
- **Fix:** Configure `OLLAMA_BASE_URL=http://host.docker.internal:11434` and add `host.docker.internal:host-gateway` to `extra_hosts` in `docker-compose.yml`.

### Issue 3: Long code artifact truncates mid-sentence
- **Root Cause:** In reasoning models (e.g. Gemini 2.5 Flash), internal reasoning tokens consume the `maxOutputTokens` quota.
- **Fix:** Ensure `"thinkingConfig": {"thinkingBudget": 0}` is set and `max_tokens` is configured to `8192` in `gemini_provider.py`.

### Issue 4: Out-of-domain queries fail to refuse
- **Root Cause:** Similarity score cutoff threshold is set too low (e.g. `0.0`).
- **Fix:** Keep `min_score = 0.05` in `vector_store.search()` and verify that the `Query Term Coverage Guard` is enabled.
