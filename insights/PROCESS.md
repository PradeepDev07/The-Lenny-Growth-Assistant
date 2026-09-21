# Engineering Process Journal (PROCESS.md)

This journal tracks the chronological development of **The Lenny Growth Assistant**. Every feature, architectural gate, test, and verification is recorded here.

---

## Phase 0 — Discovery, Environment Probing & Scaffolding

### Goal
Inspect host hardware, existing runtimes, assignment constraints, and transcripts to establish a viable, hardware-conscious architecture without making ungrounded assumptions.

### Requirements
- Address the assignment requirement for an offline local demo (via Ollama) + cloud multi-model toggle.
- Verify machine constraints (CPU, RAM, free disk space).
- Verify tool availability (Python, Node.js, Git, Docker, Ollama).
- Scaffold the `/insights` documentation system and git repository.

### Design
- Scrutinize system limits: Discovered Apple M1 MacBook Air with 8 GB unified memory and 23 GiB available disk.
- Ruled out heavy 8B+ models for baseline local operation to prevent severe unified memory starvation and swapping; selected `llama3.2:3b` or `llama3.2:1b` as the optimal local demonstration target.
- Decoupled FastAPI backend and Next.js / React frontend with direct SSE streaming.
- Dual-tier storage strategy: SQLite with standard vector similarity for frictionless local dev / testing, upgradable seamlessly to PostgreSQL + pgvector via SQLAlchemy abstraction.

### Implementation
- Initialized clean Git repository.
- Created comprehensive `.gitignore`.
- Created `/insights` documentation suite: `PROCESS.md`, `DECISION.md`, `DIFFICULTIES.md`, and `MY_UNDERSTANDING.md`.

### Files Changed
- `.gitignore`
- `insights/PROCESS.md`
- `insights/DECISION.md`
- `insights/DIFFICULTIES.md`
- `insights/MY_UNDERSTANDING.md`

### Tests
- Environment probe: Verified Python 3.12.12, Node v24.11.1, Ollama 0.34.2, Docker 29.1.2.
- Hardware probe: Verified Apple M1, 8GB RAM, 23GB disk.

### Verification
- Verified git status detects tracked insights and gitignore properly.
- Confirmed Ollama is listening locally on port 11434.

### Understanding Gate
1. Memory & Concurrency on 8GB Unified RAM.
2. Relational DB vs Vector Store data isolation.
3. Sandboxed iframe origin null security boundary.
4. Offline fallback when network drops.

### My Answer
1. 8B model will exceed unified RAM and cause OOM kills.
2. Relational DB stores consistent, permanent data; vector store is for payload chunks.
3. sandbox=allow-scripts allows scripts, omitting allow-same-origin isolates from development.
4. System falls back to local Ollama.

### Correction / Clarification
- Clarified that swap thrashing freezes macOS before an outright OOM kill.
- Clarified the query semantics difference: relational DB uses deterministic transactional filters, vector store uses approximate nearest neighbor similarity.
- Clarified that omitting allow-same-origin assigns `origin: "null"`, triggering browser SecurityErrors on cross-frame access.

### Final Understanding
The four-tier mental model is verified: Hardware budgeting < 3B, Relational/Vector separation, Iframe origin null sandbox, and resilient multi-tier fallback.

---

## Feature 1 — Minimal FastAPI Backend with Health & Config Endpoints

### Goal
Stand up the foundational HTTP backend with truthful readiness probes (`/health`) and safe public configuration inspection (`/config`) before introducing complex persistence or LLMs.

### Requirements
- Address assignment requirement for `/health` endpoint returning `{status, db: bool, ollama: bool, cloud_llm_configured: bool, version: str}`.
- Pydantic `BaseSettings` reading from `.env` and system environment variables.
- CORS middleware for Next.js frontend development (`http://localhost:3000`).
- Ensure no sensitive API keys are exposed via public endpoints.

### Design
- Async non-blocking probe using `httpx.AsyncClient` with a strict 1.5s timeout.
- Explicit Pydantic response models (`HealthResponse`, `PublicConfigResponse`) acting as strict output whitelists.
- Graceful degraded status when critical downstream dependencies (e.g., Ollama or DB) are unreachable.

### Implementation
- `backend/app/config.py`: Centralized settings parsing environment variables.
- `backend/app/schemas/health.py`: Pydantic response contracts.
- `backend/app/main.py`: FastAPI application with CORS, lifespans, `/health`, and `/config`.
- `backend/requirements.txt`: Pinned dependencies.
- `.env.example`: Documented configuration template.
- `backend/tests/test_health.py`: Automated pytest suite.

### Files Changed
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/health.py`
- `backend/requirements.txt`
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test_health.py`
- `.env.example`
- `docs/PRD.md`

### Tests
- `test_root_endpoint`: Verifies HTTP 200 and version metadata.
- `test_health_endpoint_contract`: Validates exact boolean types and contract fields.
- `test_config_endpoint_no_secrets_leaked`: Asserts no API keys or passwords are leaked in the config output.
- `test_cors_headers`: Confirms preflight OPTIONS response allows `http://localhost:3000`.
- All 4 tests passed via pytest.

### Verification
- Observed truthful `/health` behavior:
  - When Ollama was stopped: returned `status: degraded, ollama: false`.
  - When Ollama was started: returned `status: healthy, ollama: true`.

### Understanding Gate
1. What happens to concurrent requests if a synchronous I/O call blocks the asyncio event loop?
2. Why must `/config` use an explicit Pydantic response schema rather than returning raw settings?

### My Answer
1. Blocks the next process on the event loop.
2. Prevents exposing secrets like `GEMINI_API_KEY` to the client.

### Correction / Clarification
- Clarified that Python's single-threaded event loop means one blocking call stalls *all* concurrent connections (streaming tokens, health checks).
- Clarified whitelist vs. blacklist: explicit schemas guarantee future added secrets never leak by default.

### Final Understanding
Async non-blocking probes prevent event loop starvation, and strict schema DTOs enforce zero-leakage security boundaries.

### Commit
`feat: bootstrap FastAPI app with health and config endpoints`

