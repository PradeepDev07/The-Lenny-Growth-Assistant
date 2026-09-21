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
`da17ae4` — `feat: bootstrap FastAPI app with health and config endpoints`

---

## Feature 2 — Database Models, Session Persistence & Messaging Endpoints

### Goal
Implement transactional conversation storage for sessions, chronological messages, source citations, generated artifacts, and routing audit logs, with automatic cascade deletion and dual database engine compatibility.

### Requirements
- Address assignment requirement for session and message persistence.
- Models: `Session`, `Message`, `Artifact`, `RoutingLog`.
- Async engine supporting SQLite (local dev) and PostgreSQL (production).
- Endpoints: `POST /api/sessions`, `GET /api/sessions`, `GET /api/sessions/{id}`, `DELETE /api/sessions/{id}`, `POST /api/sessions/{id}/messages`.
- Consistent error responses: `{ "error": { "code": "...", "message": "..." } }`.
- Active DB connectivity probe in `GET /health` (`SELECT 1`).

### Design
- SQLAlchemy 2.0 async declarative models with typed `Mapped[...]`.
- SQLite event listener setting `PRAGMA foreign_keys = ON` on connection so database-level cascade deletion behaves identically to PostgreSQL.
- Repository pattern (`SessionRepository`) isolating SQL queries and count subqueries from route handlers.
- Custom FastAPI exception handler for `HTTPException` standardizing error payload schemas.

### Implementation
- `backend/app/db/session.py`: Async engine, session factory, and `init_db`.
- `backend/app/models/entities.py`: `SessionModel`, `MessageModel`, `ArtifactModel`, `RoutingLogModel`.
- `backend/app/schemas/session.py`: Pydantic validation schemas with `ConfigDict(from_attributes=True)`.
- `backend/app/db/repository.py`: Async repository with cascade deletes, count subqueries, and message ordering.
- `backend/app/routers/sessions.py`: REST CRUD router.
- `backend/app/main.py`: Connected router, added active `SELECT 1` probe to `/health`, and registered global `HTTPException` handler.
- `backend/tests/test_sessions.py`: Integration tests.

### Files Changed
- `backend/app/db/__init__.py`
- `backend/app/db/session.py`
- `backend/app/db/repository.py`
- `backend/app/models/__init__.py`
- `backend/app/models/entities.py`
- `backend/app/schemas/session.py`
- `backend/app/routers/__init__.py`
- `backend/app/routers/sessions.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/tests/test_sessions.py`

### Tests
- `test_session_lifecycle_and_cascade_deletion`: Full CRUD cycle, verified chronological order, and directly verified 0 orphaned messages after session deletion.
- `test_add_message_to_non_existent_session_returns_404`: Verified structured error response.
- All 6 tests passing (4 health + 2 persistence).

### Verification
- Executed live API test: created session `e6f1c428...`, added message with citations and model info, verified retrieval, and verified `/health` returned `db: True` via live query.

### Understanding Gate
1. What happens in the database if a user deletes a session and cascade deletion is NOT configured?
2. Why must message history be queried strictly filtered by `session_id`?

### My Answer
Initially answered "not sure", then walked through folder/paper analogy and confirmed understanding.

### Correction / Clarification
- Clarified that without cascade deletion, child records become orphaned ghost data or trigger foreign key violation errors.
- Clarified that mixing sessions cross-contaminates prompt context and exhausts finite token limits.

### Final Understanding
Cascade deletion maintains relational integrity atomically, and session filtering protects conversation isolation and prompt context windows.

### Commit
`1a43b35` — `feat: add async persistence for sessions and messages with cascade deletion`

---

## Feature 3 — Multi-Provider LLM Abstraction Layer & Task-Based Router

### Goal
Decouple the application from vendor-specific LLM SDKs through a normalized provider adapter interface and a task-based router supporting cascading fallback to local Ollama with audit telemetry.

### Requirements
- Address assignment requirement for multi-provider support: Google Gemini, OpenRouter, and local Ollama.
- Normalized interface returning standardized `LLMResponse` and token streams.
- Task-based model routing (`intent_routing`, `retrieval_qa`, `essay_generation`, `artifact_generation`, `offline_demo_mode`).
- Graceful cascading fallback on network timeout, 429 quota limits, or missing API keys.
- Audit logging of model latency and fallback flags into `routing_logs`.

### Design
- Abstract base class `BaseLLMProvider` defining `generate(...)` and `stream(...)`.
- `OllamaProvider`: Native REST client for `/api/chat` with non-streaming and streaming NDJSON parsing.
- `GeminiProvider`: Google Gemini direct REST client for high-context RAG Q&A.
- `OpenRouterProvider`: OpenAI-compatible multi-model client for Claude 3.7 / GPT-4o essay generation.
- `TaskRouter`: Maps tasks to prioritized provider sequences and cascades on failure.

### Implementation
- `backend/app/llm/base.py`: `LLMMessage`, `LLMResponse`, `BaseLLMProvider`.
- `backend/app/llm/ollama_provider.py`: Local Ollama adapter.
- `backend/app/llm/gemini_provider.py`: Google Gemini adapter.
- `backend/app/llm/openrouter_provider.py`: OpenRouter multi-model adapter.
- `backend/app/llm/router.py`: `TaskRouter` and global `model_router` singleton.
- `backend/app/llm/__init__.py`: Export LLM layer.
- `backend/tests/test_llm_providers.py`: Automated tests.

### Files Changed
- `backend/app/llm/__init__.py`
- `backend/app/llm/base.py`
- `backend/app/llm/ollama_provider.py`
- `backend/app/llm/gemini_provider.py`
- `backend/app/llm/openrouter_provider.py`
- `backend/app/llm/router.py`
- `backend/tests/test_llm_providers.py`

### Tests
- `test_llm_response_normalization`: Verifies standard contract fields.
- `test_provider_availability_checks`: Verifies availability logic based on keys.
- `test_task_router_chain_order`: Asserts proper priority chains per task.
- `test_cascading_fallback_and_telemetry`: Simulated primary provider failure, verified automatic fallback to local tier with `fallback_used: True`, and verified DB audit log written to `routing_logs`.
- All 10 tests passed via pytest.

### Verification
- Executed live inference test against host Ollama daemon: generated real tokens with 1364ms latency and normalized `LLMResponse`.

### Understanding Gate
1. Why does returning a standardized `LLMResponse` matter to the layers sitting above the LLM?
2. If the app is served over HTTPS in production, how can it call an HTTP Ollama daemon without browser mixed-content blocks?

### My Answer
1. It standardizes key names and data structure so upstream code doesn't break if vendor payloads differ.
2. Correctly noted fallback, but raised the production HTTPS / HTTP Ollama mixed-content challenge.

### Correction / Clarification
- Clarified that the browser never connects to Ollama directly; all Ollama calls occur strictly server-side (FastAPI to loopback or Docker private network). The browser only ever sees encrypted HTTPS to the backend.

### Final Understanding
Adapter normalization protects upstream code from vendor API churn, cascading fallback guarantees resilience, and server-side execution bypasses browser mixed-content policies.

### Commit
`b058c22` — `feat: add multi-provider LLM layer and task router with cascading fallback`

---

## Feature 4 — Transcript Ingestion, Semantic Chunking & Vector Retrieval Engine

### Goal
Ingest Lenny's Podcast transcripts, segment them into speaker-aware overlapping semantic chunks, build a boosted vector/BM25 retrieval engine, and calibrate thresholding to refuse out-of-domain queries.

### Requirements
- Address assignment requirement for transcript ingestion and retrieval pipeline.
- Curated episodes ingested: Brian Balfour (Growth Loops), Elena Verna (PLG & Activation), Lenny Rachitsky (PMF 0-to-1), Shreyas Doshi (PM Metrics & LNO).
- Chunking preserving speaker context, episode metadata (`episode_id`, `guest`, `title`, `url`), and deterministic chunk IDs.
- CLI script: `python -m ingestion.ingest --refresh`.
- Rejection of out-of-domain / irrelevant queries (returning empty list `[]` to trigger grounded refusal).

### Design
- `ingestion/chunker.py`: Normalizes text, splits on dialogue paragraphs (~1200 characters / ~400–600 tokens), with 200 character overlap to maintain context continuity.
- `backend/app/retrieval/vector_store.py`: Persistent vector/document store with metadata field boosting (2.5x guest name, 1.8x episode title), stopword filtering, and query term coverage validation (requiring at least 2 content terms for queries with 3+ terms).
- Fast disk cache persistence (`vector_cache.json`).

### Implementation
- `ingestion/data/`: Copied 4 curated transcript JSON files.
- `ingestion/chunker.py`: Semantic dialogue chunking logic.
- `ingestion/ingest.py`: Ingestion CLI runner with `--refresh` flag.
- `backend/app/retrieval/vector_store.py`: BM25/vector store with metadata boosting, stopword removal, and coverage guard.
- `backend/app/retrieval/__init__.py`: Package exports.
- `backend/tests/test_retrieval.py`: Comprehensive automated retrieval unit tests.

### Files Changed
- `ingestion/__init__.py`
- `ingestion/chunker.py`
- `ingestion/ingest.py`
- `ingestion/data/*.json`
- `backend/app/retrieval/__init__.py`
- `backend/app/retrieval/vector_store.py`
- `backend/tests/test_retrieval.py`
- `insights/QA.md`
- `insights/MY_UNDERSTANDING.md`

### Tests
- `test_chunker_metadata_and_overlap`: Validates metadata preservation and chunk continuity.
- `test_retrieval_brian_balfour_growth_loops`: Validates top rank recall for loops vs funnels.
- `test_retrieval_elena_verna_activation`: Validates top rank recall for PLG activation metrics.
- `test_retrieval_shreyas_doshi_lno_framework`: Validates top rank recall for LNO framework.
- `test_retrieval_lenny_pmf_signals`: Validates top rank recall for PMF indicators.
- `test_similarity_threshold_rejects_unrelated_queries`: Asserts quantum mechanics, brownie recipes, and car repair return 0 results (`[]`).
- All 16 backend tests passed via pytest.

### Verification
- Ran `python -m ingestion.ingest --refresh`: successfully indexed 10 chunks from 4 episodes into `vector_cache.json`.

### Understanding Gate
1. Why can't a normal PostgreSQL B-tree index answer semantic proximity queries?
2. What happens if similarity threshold is set to `0.0` vs. `0.98`?

### My Answer
1. Relational DB checks exact/scalar values; cannot compare semantic vectors.
2. Threshold 0.0 sends irrelevant chunks and causes hallucinations; 0.98 was assumed to give very similar answers.

### Correction / Clarification
- Clarified that in high-dimensional dense space, natural queries rarely score 0.98 unless verbatim identical. Setting 0.98 causes catastrophic over-refusal / false negatives. Calibrated thresholds (Goldilocks zone ~0.45–0.55) balance recall and refusal.

### Final Understanding
Vector search navigates multi-dimensional space, and threshold calibration prevents both hallucinations (too low) and over-refusals (too high).

### Commit
`1888d1e` — `feat: add transcript chunking, boosted vector retrieval, and ingestion CLI`

---

## Feature 5 — Grounded RAG Chat Engine with Streaming SSE & Source Citations

### Goal
Implement end-to-end grounded conversational RAG using Server-Sent Events (SSE), XML prompt delimiter boundaries, source attribution, and conversation persistence.

### Requirements
- Address assignment requirement for grounded RAG conversational assistant.
- Real-time token streaming via SSE (`text/event-stream`).
- XML-delimited prompt compiler to prevent prompt injection and guarantee evidence grounding.
- Inline citations in `[Lenny Podcast — Guest — Episode Title]` format.
- Graceful refusal when retrieval returns empty array `[]` ("not covered in archive").
- Persist user message immediately and assistant message with sources upon stream completion.

### Design
- `backend/app/rag/engine.py`: XML prompt compiler (`<transcript_evidence>` vs `<user_question>`), RAG orchestrator, and streaming generator.
- `backend/app/routers/chat.py`: `POST /api/chat` returning `StreamingResponse`.
- Streaming protocol: yields `data: {"token": "..."}\n\n` and terminates with `data: {"event": "done", "sources": [...], "model_info": {...}}\n\n`.
- Post-stream database finalization: writes assistant response, source citations, and telemetry into `messages` and `routing_logs`.

### Implementation
- `backend/app/schemas/session.py`: Added `ChatRequest`.
- `backend/app/rag/engine.py`: Grounded RAG streaming pipeline.
- `backend/app/rag/__init__.py`: Package exports.
- `backend/app/routers/chat.py`: SSE endpoint with session validation.
- `backend/app/routers/__init__.py`: Export chat router.
- `backend/app/main.py`: Registered `/api/chat`.
- `backend/tests/test_chat.py`: Automated integration tests.

### Files Changed
- `backend/app/schemas/session.py`
- `backend/app/rag/__init__.py`
- `backend/app/rag/engine.py`
- `backend/app/routers/chat.py`
- `backend/app/routers/__init__.py`
- `backend/app/main.py`
- `backend/tests/test_chat.py`
- `insights/PROCESS.md`
- `insights/DECISION.md`
- `insights/QA.md`

### Tests
- `test_build_grounding_prompt_compilation`: Verified XML delimiter formatting.
- `test_build_grounding_prompt_empty_chunks`: Verified empty evidence block formatting.
- `test_chat_non_existent_session_returns_404`: Verified 404 with structured error.
- `test_chat_grounded_streaming_and_persistence`: Verified SSE token streaming, source attribution, and message persistence.
- `test_chat_refusal_when_retrieval_empty`: Verified refusal text and empty sources on unrelated query.
- All 21 tests in suite passed.

### Verification
- Executed live streaming test against host Ollama `llama3.2:3b`.

### Understanding Gate
1. What must the system prompt instruct the model to do when retrieval returns `[]`?
2. Why send source citations and latency at the end of the SSE stream?

### My Answer
1. Delimiters treat evidence as data and user prompt as query; if empty, return insufficient data rather than hallucinating from pre-trained weights.
2. SSE avoids waiting spinners; latency and sources are only finalized after stream completion.

### Correction / Clarification
- Highlighted progressive disclosure in UI design: sending citations at the end prevents layout shifts while reading streamed tokens.

### Final Understanding
XML delimiter isolation establishes authority boundaries, and SSE streaming with end-of-stream finalization balances latency with structured metadata delivery.

### Commit
`8d5b90c` — `feat: implement grounded RAG chat with streaming SSE and source citations`

---

## Feature 6 — Ship 30 for 30 Essay-Writing Skill Engine

### Goal
Implement a dedicated skill engine that transforms Lenny podcast insights into structured, publication-ready digital essays (~1,250 words) adhering to the Ship 30 for 30 atomic writing methodology.

### Requirements
- Address assignment requirement for Ship 30 for 30 essay generation.
- Strict 6-stage compositional scaffolding:
  1. Hook (1 provocative opening sentence)
  2. 1-3-1 Cadence (short assertion, 3 tension lines, transition)
  3. PM / Founder Observed Narrative (2-3 paragraphs)
  4. Core Framework Breakdown (bulleted, bold headlines, grounded with inline citations)
  5. Practical Application: 3 Actionable Takeaways (Monday morning execution)
  6. Anchor Conclusion (memorable rule of thumb)
- Topic retrieval: vector search finds relevant podcast excerpts to ground claims.
- Cloud priority routing via `task="essay_generation"` with automatic local Ollama fallback.
- Stream tokens via SSE (`text/event-stream`).
- Dual persistence: saves both conversational message and persistent `ArtifactModel` record (`type="markdown"`).
- Artifact inspection endpoints: `GET /api/artifacts/{id}` and `GET /api/sessions/{id}/artifacts`.

### Design
- `backend/app/skills/ship30.py`: Structural prompt compiler and SSE generator.
- `backend/app/schemas/skill.py`: Pydantic models `EssayRequest`, `EssayResponse`.
- `backend/app/routers/skills.py`: `POST /api/skills/essay`, `GET /api/artifacts/{id}`, `GET /api/sessions/{id}/artifacts`.
- `backend/app/db/repository.py`: Added `add_artifact`, `get_artifacts`, and `get_artifact`.

### Implementation
- `backend/app/schemas/skill.py`: Request/response models.
- `backend/app/schemas/session.py`: Added `ArtifactResponse`.
- `backend/app/skills/ship30.py`: Ship 30 prompt builder and streaming pipeline.
- `backend/app/skills/__init__.py`: Package exports.
- `backend/app/routers/skills.py`: FastAPI routes for skills and artifacts.
- `backend/app/routers/__init__.py`: Registered skills router.
- `backend/app/main.py`: Included `skills_router`.
- `backend/tests/test_skills.py`: 6 automated integration tests.

### Files Changed
- `backend/app/schemas/session.py`
- `backend/app/schemas/skill.py`
- `backend/app/skills/__init__.py`
- `backend/app/skills/ship30.py`
- `backend/app/routers/skills.py`
- `backend/app/routers/__init__.py`
- `backend/app/main.py`
- `backend/app/db/repository.py`
- `backend/tests/test_skills.py`
- `insights/PROCESS.md`
- `insights/DECISION.md`
- `insights/QA.md`

### Tests
- `test_ship30_prompt_compilation`: Verified all 6 structural stages, citation format, and XML delimiters.
- `test_ship30_prompt_empty_chunks`: Verified refusal marker on empty evidence.
- `test_generate_essay_endpoint_streaming_and_artifact_persistence`: Verified SSE streaming, DB artifact creation, and artifact retrieval endpoints.
- `test_generate_essay_auto_creates_session`: Verified session auto-creation when session_id is omitted.
- `test_generate_essay_refusal_on_unrelated_topic`: Verified refusal without artifact generation on out-of-domain queries.
- `test_generate_essay_non_existent_session_returns_404`: Verified 404 response on invalid session ID.
- Full test suite: 27/27 tests passed in 0.69s.

### Verification
- Pytest verified complete end-to-end integration and mock streaming.

### Understanding Gate
1. Why smaller models collapse to 200–300 words without scaffolding, and how step-by-step XML directives prevent it.
2. Hardware and quality tradeoffs between short Q&A (local Ollama) and long essays (cloud priority with local fallback).

### My Answer
1. Small model has low context memory by default; without structured prompt it produces 200-300 words; explicit prompt generates proper structure.
2. 8B model swaps and causes lag on low RAM; context memory is affected.

### Correction / Clarification
- Clarified transformer autoregressive token prediction: without explicit sub-task checkpoints, attention heads trigger premature concluding tokens.
- Quantified the generation time tradeoff: 1,800 tokens locally takes ~60-75s of continuous GPU saturation vs ~15s on cloud, making cloud routing with offline local fallback optimal.

### Final Understanding
Structural scaffolding provides autoregressive pacing, and task-based routing balances local privacy for chat against cloud throughput for long-form synthesis.

### Commit
`9379bf5` — `feat: implement Ship 30 for 30 essay skill engine with structural scaffolding and artifact persistence`

---

## Feature 7 — Sandboxed Interactive Artifact Generation Engine & Security Sandbox

### Goal
Implement an interactive artifact generation engine that compiles podcast frameworks into standalone, reactive HTML/JS/CSS calculators and tools, securely isolated inside a two-layer defense-in-depth sandbox.

### Requirements
- Address assignment requirement for interactive artifact generation and sandboxed rendering.
- Single-file self-contained HTML contract (inline `<style>`, inline vanilla `<script>`, zero remote CDN calls).
- Grounded in Lenny's Podcast transcripts with citation header: `[Lenny Podcast — Guest Name — Episode Title]`.
- Route via `task="artifact_generation"` prioritizing cloud models with local Ollama fallback.
- Stream tokens via SSE (`text/event-stream`).
- Persist artifact as `ArtifactModel(type="html", ...)`.
- Security Sandbox:
  - Raw endpoint `GET /api/artifacts/{id}/raw` serving `text/html`.
  - HTTP `Content-Security-Policy`: `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; frame-ancestors 'self' http://localhost:3000 http://127.0.0.1:3000;`.
  - HTTP `X-Content-Type-Options: nosniff`.
  - Frontend Iframe contract: `sandbox="allow-scripts"` strictly omitting `allow-same-origin` (setting `origin: "null"`).

### Design
- `backend/app/skills/interactive.py`: Single-file HTML prompt compiler and SSE generator.
- `backend/app/routers/skills.py`: Added `POST /api/skills/artifact` and `GET /api/artifacts/{id}/raw`.
- Two-layer defense-in-depth:
  - Layer 1 (Vertical Isolation): Iframe null origin prevents child scripts from accessing `window.parent.localStorage` or cookies.
  - Layer 2 (Horizontal Containment): CSP `connect-src 'none'` physically blocks outbound `fetch`, `XHR`, `WebSocket`, and tracking beacons from exfiltrating calculation inputs.

### Implementation
- `backend/app/schemas/skill.py`: Added `InteractiveArtifactRequest`.
- `backend/app/schemas/__init__.py`: Exported `InteractiveArtifactRequest`.
- `backend/app/skills/interactive.py`: Interactive tool generator and grounding prompt.
- `backend/app/skills/__init__.py`: Exported interactive skill functions.
- `backend/app/routers/skills.py`: Added `POST /api/skills/artifact` and `GET /api/artifacts/{id}/raw`.
- `backend/tests/test_artifacts.py`: 6 automated integration tests.

### Files Changed
- `backend/app/schemas/skill.py`
- `backend/app/schemas/__init__.py`
- `backend/app/skills/interactive.py`
- `backend/app/skills/__init__.py`
- `backend/app/routers/skills.py`
- `backend/tests/test_artifacts.py`
- `insights/PROCESS.md`
- `insights/DECISION.md`
- `insights/QA.md`

### Tests
- `test_interactive_artifact_prompt_compilation`: Verified single-file contract, zero-network sandbox rules, and podcast citations.
- `test_interactive_artifact_prompt_empty_chunks`: Verified archive refusal prompt when no chunks match.
- `test_generate_interactive_artifact_endpoint_and_csp_headers`: Verified SSE streaming, code fence stripping, DB persistence as type="html", and CSP headers on `/raw`.
- `test_raw_endpoint_renders_markdown_safely`: Verified markdown raw preview container with identical CSP.
- `test_generate_artifact_refusal_on_irrelevant_topic`: Verified refusal on unrelated requests.
- `test_artifact_raw_404_on_invalid_id`: Verified structured 404 response on missing artifact.
- Full test suite: 33/33 tests passed in 1.14s.

### Verification
- Pytest verified complete end-to-end integration and mock streaming.

### Understanding Gate
1. Why specifying `sandbox="allow-scripts"` while strictly omitting `allow-same-origin` is essential, and what runtime error occurs on parent access.
2. How Content Security Policy (`connect-src 'none'`) blocks outward data exfiltration even if origin isolation is intact.

### My Answer
1. Need JS for interactive dynamic response; omit allow-same-origin so iframe doesn't have direct access to parent container.
2. Not sure.

### Correction / Clarification
- Explained that omitting `allow-same-origin` assigns opaque `origin: "null"`, triggering `DOMException: Blocked a frame with origin "null" from accessing a cross-origin frame`.
- Explained the dual threat model: origin isolation blocks inward privilege escalation, while `CSP: connect-src 'none'` and `img-src data:` block outward network exfiltration of confidential metrics entered into calculators.

### Final Understanding
Two-layer defense-in-depth: `origin: null` establishes vertical privilege isolation, while `CSP: connect-src 'none'` guarantees zero outward network leakage.

### Commit
`e5cc5fa` — `feat: implement sandboxed interactive artifact generation engine with defense-in-depth CSP`





