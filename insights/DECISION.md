# Architectural Decision Records (DECISION.md)

This document records the architectural and engineering decisions made during the design and construction of **The Lenny Growth Assistant**.

---

# Decision 001: Hardware-Conscious Local Model Selection (Apple M1 8GB RAM)

## Context
The project requires a local offline demonstration using Ollama alongside the web server, database, vector search, and frontend. The development host is an Apple MacBook Air M1 with 8 GB of unified memory and 23 GiB of free disk space.

## Options Considered

### Option A: Standard 8B parameter model (`llama3.1:8b` or `llama2:7b`)
- Requires ~4.8 GB - 5.5 GB of RAM when loaded at 4-bit quantization.
- Leaves less than 2.5 GB for macOS, Chrome/browser, Python runtime, Docker/Postgres, and Node.js.
- Would cause immediate memory swapping (thrashing the SSD), high latency (tokens/sec crawling below 2-4 t/s), and potential OOM kernel kills.

### Option B: Ultra-lightweight model (`smollm:135m` or `llama3.2:1b`)
- Extremely low memory footprint (<1 GB).
- However, 135M models struggle with complex instruction following, structured JSON emission, and accurate source synthesis. 1B is decent for classification but weak for structured generation.

### Option C: Compact high-performance model (`llama3.2:3b` or `qwen2.5:3b`)
- Requires ~2.0 GB - 2.2 GB of RAM at Q4_K_M.
- State-of-the-art reasoning and instruction-following for its weight class.
- Leaves >5 GB headroom for the operating system and application services.
- Delivers 25-35 tokens/sec on Apple Silicon M1 Metal acceleration.

## Decision
We select **`llama3.2:3b`** (with `llama3.2:1b` as a backup lightweight tier) for the local Ollama demo baseline.

## Why
It satisfies the requirement for local execution without exceeding the physical hardware boundary of the 8GB M1 Mac.

## Trade-offs
A 3B model is slightly less nuanced than an 8B or 70B cloud model in synthesizing deeply nuanced multi-turn conversation. To mitigate this, our prompts must provide explicit, high-signal context and structured output templates.

## Alternatives Rejected
`llama3.1:8b` was rejected because running an 8B model on an 8GB machine with Docker, React, and Python active will degrade system performance and induce swap thrashing.

## Consequences
Prompt engineering for the local fallback must avoid excessively lengthy system contexts and prefer tight, structured prompt schemas.

## Revisit Conditions
If run on a machine with 16GB+ RAM or a dedicated GPU with 8GB+ VRAM, `llama3.1:8b` or `qwen2.5:7b` can be enabled via configuration.

---

# Decision 002: Dual-Tier Persistence Strategy (PostgreSQL / SQLite Fallback)

## Context
The system requires persistence for chat sessions, conversation messages, source citations, routing telemetry, and generated artifacts. While production topologies typically utilize PostgreSQL with `pgvector`, setting up and running a local Dockerized PostgreSQL instance requires running Docker Desktop, consuming additional memory on an 8GB RAM machine.

## Options Considered

### Option A: Postgres-only with Docker dependency
- Standard production stack.
- Consumes ~1.5 GB - 2 GB RAM just for Docker Desktop VM overhead on macOS.
- Makes the app fail to boot if Docker is not started.

### Option B: SQLite-only
- Zero RAM overhead, no background daemon required, embedded in Python process.
- Lacks native high-scale vector indexing (unless using sqlite-vec extensions).

### Option C: SQLAlchemy Abstraction with Postgres + SQLite Pluggable Engine
- Abstract all ORM models (Sessions, Messages, Artifacts, Routing Logs) through SQLAlchemy.
- If `DATABASE_URL` specifies `postgresql://`, connect to Postgres (with pgvector).
- If `DATABASE_URL` is unset or points to `sqlite:///`, seamlessly operate on SQLite with in-memory / flat vector cosine similarity computation.

## Decision
We choose **Option C: SQLAlchemy Abstraction with Postgres + SQLite Pluggable Engine**.

## Why
This provides immediate zero-config local runnability (the app starts in 1 second without Docker) while remaining 100% compliant with the production Docker Compose / PostgreSQL requirement.

## Trade-offs
We maintain standard SQL models and avoid database-specific proprietary features in the primary application layer.

## Alternatives Rejected
Option A was rejected as a strict hard-requirement for local dev because Docker was verified to be inactive on host startup, and forcing Docker VM overhead would heavily strain 8GB RAM.

## Consequences
Database schemas must use portable types (e.g. JSON types supported by both Postgres and SQLite via SQLAlchemy `JSON`).

---

# Decision 003: Model Provider Layer & Task-Based Router Architecture

## Context
The application must support:
1. Local offline model (Ollama).
2. Direct Cloud LLM (Google Gemini direct SDK/REST for large-context RAG Q&A).
3. Multi-model routing (OpenRouter for high-capability models e.g. Claude 3.7 Sonnet / GPT-4o for essay generation).

## Options Considered

### Option A: Hardcoded LLM calls scattered in route handlers
- Fast to code initially.
- Disastrous for maintainability, testing, and fallback.

### Option B: Provider Adapter Pattern with Central Task Router
- Implement a unified `BaseLLMProvider` interface returning normalized `LLMResponse` and `AsyncIterator[str]` streams.
- Implement concrete providers: `OllamaProvider`, `GeminiProvider`, `OpenRouterProvider`.
- Implement a declarative `TaskRouter` that maps task types (`intent_routing`, `retrieval_qa`, `essay_generation`, `artifact_generation`) to primary, secondary, and local fallback providers.

## Decision
We select **Option B: Provider Adapter Pattern with Central Task Router**.

## Why
Clean separation of concerns: RAG, the Ship 30 skill, and artifact generation ask for a *task*, not a vendor. If a cloud API key is missing or hits a rate limit, the router silently cascades down the fallback chain to Ollama.

## Trade-offs
Requires a small initial overhead of interface definition and normalization of tokens/latencies.

## Alternatives Rejected
Direct database queries were rejected because they tightly couple route handling with SQL dialects and make repository-level unit testing impossible.

---

# Decision 006: Abstract Provider Adapter Pattern (Liskov Substitution Principle)

## Context
Different LLM providers (Ollama, Google Gemini, OpenRouter) format inputs and outputs differently. If route handlers or RAG pipelines call vendor SDKs directly, swapping models or falling back on error requires rewriting business logic.

## Options Considered

### Option A: Direct third-party SDK calls in routes
- High coupling, leaky abstractions, fragmented error handling.

### Option B: Provider Adapter Pattern with Normalization (`BaseLLMProvider`)
- Standardized abstract methods: `generate(...)` and `stream(...)`.
- Standardized return type: `LLMResponse(text, prompt_tokens, completion_tokens, latency_ms, provider, model, fallback_used)`.

## Decision
We select **Option B: Provider Adapter Pattern with Normalization**.

## Why
Any provider can be substituted for another without modifying a single line of business or RAG logic.

---

# Decision 007: Task-Based Model Routing with Automated Local Fallback

## Context
Different tasks have different performance and cost profiles:
- Long-form Ship 30 essays need strong literary reasoning (Claude 3.7 Sonnet).
- Grounded RAG Q&A needs huge context windows and low latency (Gemini 2.5 Flash).
- Offline evaluation requires running on localhost without cloud keys (Ollama).

## Options Considered

### Option A: Static hardcoded model across all endpoints
- Weak essays if using a fast model, or high latency and cost if using a reasoning model for simple tasks. Zero offline resilience.

### Option B: Rule-based TaskRouter with Cascading Fallback Chains
- Configurable task mappings with fallback chains: `[Primary Cloud, Secondary Cloud, Local Ollama]`.
- Network errors or 429 quota exceptions automatically trigger cascade to the next tier without crashing the user request.
- Every routing event logs telemetry to `routing_logs`.

## Decision
We select **Option B: Rule-based TaskRouter with Cascading Fallback Chains**.

## Why
Delivers optimal quality-per-task, zero-crash resilience during internet drops, and complete observability into model latency and fallback rates.

---

# Decision 008: Semantic Dialogue Chunking with Sliding Window Overlap

## Context
Lenny's Podcast transcripts are long conversational transcripts. Splitting text arbitrarily across characters breaks questions and answers mid-sentence.

## Options Considered

### Option A: Fixed-size character or token chunking without boundary awareness
- Simple to write.
- Cuts sentences in half, causing fragmented context and incomplete thoughts in retrieved chunks.

### Option B: Dialogue-aware paragraph chunking with sliding overlap (~1200 chars / ~400–600 tokens, 200 char overlap)
- Splits on natural paragraph/speaker boundaries.
- Overlap ensures concepts bridging chunk boundaries are never lost to retrieval.
- Attaches structured metadata (`episode_id`, `guest`, `title`, `url`, `chunk_index`).

## Decision
We select **Option B: Dialogue-aware paragraph chunking with sliding overlap**.

## Why
Preserves conversational integrity, speaker identity, and provides rich citation metadata for grounding.

---

# Decision 009: BM25 Metadata Boosting with Query Term Coverage Guard

## Context
Plain keyword search treats all words equally. In podcasts, matching a guest name (e.g., "Elena Verna") or an episode title (e.g., "Growth Loops") is much higher signal than a generic word. Furthermore, unconstrained scoring causes queries with common verbs (e.g. "change" in "how to change car fluid") to match unrelated chunks.

## Options Considered

### Option A: Plain BM25 without field weights or stopword filtering
- Struggles when the user asks for a specific guest by name, and returns false positives on common verbs.

### Option B: Field-Boosted BM25 with Stopword Filtering and Query Term Coverage Guard
- 2.5x boost for matches in the `guest` field.
- 1.8x boost for matches in the `source_title` field.
- Stopword filtering to remove generic English noise words.
- Query Term Coverage Guard: multi-term queries (3+ terms) must match at least 2 distinct content terms, eliminating single-word lexical flukes.
- Calibrated similarity threshold (`min_score`): scores below the threshold return `[]` to trigger grounded refusal.

## Decision
We select **Option B: Field-Boosted BM25 with Stopword Filtering and Query Term Coverage Guard**.

## Why
Guarantees high precision for domain queries and deterministic refusal for out-of-domain queries.

---

# Decision 010: Delimited XML Grounding Contract for Prompt Injection Defense

## Context
When blending system instructions, retrieved transcript excerpts, conversation history, and raw user input into a single LLM prompt, adversarial user prompts can attempt to hijack instructions (prompt injection), or models may blend training assumptions with transcript facts.

## Options Considered

### Option A: Free-form text concatenation
- Concatenates "Here are excerpts: ... Here is the user: ...".
- Vulnerable to prompt injection; model easily confuses user text with system rules.

### Option B: Strict XML-delimited prompt encapsulation
- Encapsulates retrieved excerpts inside `<transcript_evidence>...</transcript_evidence>`.
- Encapsulates user questions inside `<user_question>...</user_question>`.
- System instructions explicitly declare: `<user_question>` has zero authority to redefine rules; if `<transcript_evidence>` lacks facts, model is bound to state insufficient evidence.

## Decision
We select **Option B: Strict XML-delimited prompt encapsulation**.

## Why
Provides a robust structural defense against prompt injection and forces model grounding exclusively in retrieved text.

---

# Decision 011: Server-Sent Events (SSE) Unidirectional Token Streaming Protocol

## Context
Conversational AI requires immediate token streaming so users do not stare at loading spinners for 5+ seconds.

## Options Considered

### Option A: Full-duplex WebSockets
- Heavyweight stateful connection; difficult proxy and reconnect management.

### Option B: Server-Sent Events (SSE) via FastAPI StreamingResponse
- Standard HTTP (`text/event-stream`).
- Pushes incremental `data: {"token": "..."}\n\n` events.
- Emits termination payload `data: {"event": "done", "sources": [...], "model_info": {...}}\n\n`.
- Supported natively by browsers and proxies with automatic reconnection.

## Decision
We select **Option B: Server-Sent Events (SSE)**.

## Why
Simplest production-grade streaming protocol, zero socket overhead, and natural progressive disclosure of citation cards.




---

# Decision 004: Foreign Key Enforcement & Cascade Deletion in Dual-Engine Setup

## Context
When a user deletes a session, all associated messages and generated artifacts must be deleted to prevent orphaned records. PostgreSQL enforces foreign keys and cascade rules natively. SQLite, however, disables foreign key enforcement by default on every new connection for backwards compatibility.

## Options Considered

### Option A: Manual application-level deletion
- Execute `DELETE FROM messages WHERE session_id = ...`, then `DELETE FROM artifacts ...`, then `DELETE FROM sessions ...` manually in Python code.
- Prone to race conditions, partial deletion on crash, and leaves orphaned records if any step fails.

### Option B: Database-level cascade with SQLite connection hook
- Declare `ForeignKey("sessions.id", ondelete="CASCADE")` and SQLAlchemy `cascade="all, delete-orphan"` on the models.
- Attach an event listener `@event.listens_for(engine.sync_engine, "connect")` that immediately issues `PRAGMA foreign_keys=ON` on every SQLite connection.

## Decision
We select **Option B: Database-level cascade with SQLite connection hook**.

## Why
It guarantees atomic, single-transaction cascade deletion across both SQLite in development and PostgreSQL in production without manual query bookkeeping.

---

# Decision 005: Async Repository Pattern for Storage Isolation

## Context
Route handlers in FastAPI could directly query the database via SQLAlchemy `session.execute(select(...))`.

## Options Considered

### Option A: Direct database queries inside router functions
- Faster to write for 1 or 2 routes.
- Highly couples HTTP routing and serialization logic with database queries. Makes changing query mechanics (e.g. adding pagination, count subqueries, caching) require editing every route.

### Option B: Dedicated Async Repository Layer (`SessionRepository`)
- Encapsulates queries, subqueries, and updates inside static async methods.
- Route handlers only handle request validation, dependency injection, and response mapping.

## Decision
We select **Option B: Dedicated Async Repository Layer**.

## Why
Clean separation of concerns, testability, and centralized SQL query maintenance.

---

# Decision 009: Ship 30 for 30 Structural Prompt Scaffolding & Artifact Decoupling

## Context
Small local models (~3B parameters) lack working memory to pace themselves for long-form ~1,250-word essays and naturally collapse into 200–300 word summaries when given open-ended instructions. Furthermore, essay generation takes significantly longer than interactive chat (1,800 tokens vs 200 tokens) and produces self-contained editorial output that users need to save, copy, and inspect independently of conversational chat bubbles.

## Options Considered

### Option A: Open-ended chat prompt ("Write a 1250-word essay about...")
- Fails on small models due to premature token convergence.
- Treats essay as normal chat messages without distinct artifact lifecycle.

### Option B: Hierarchical 6-Stage Scaffolding with Dual Persistence (Message + ArtifactModel)
- Define a 6-stage compositional scaffolding: Hook (1 sentence), 1-3-1 Cadence, Narrative, Core Framework Breakdown (bulleted with inline citations), Practical Application (3 Takeaways), and Anchor Conclusion.
- Route via `task="essay_generation"` prioritizing high-throughput cloud models (`gemini` -> `openrouter` -> `ollama`) to prevent 70-second GPU thrashing on 8GB host RAM.
- Stream tokens via SSE and atomically persist the completed essay as an `ArtifactModel` record (`type="markdown"`), enabling the frontend split-pane view (chat on left, rendered artifact on right).

## Decision
We select **Option B: Hierarchical 6-Stage Scaffolding with Dual Persistence**.

## Why
Prevents prompt collapsing, bounds local hardware usage, guarantees citation grounding, and generates first-class artifacts ready for distribution.

---

# Decision 010: Defense-in-Depth Interactive Artifact Sandbox

## Context
Interactive single-page HTML/JS tools (such as Elena Verna's activation calculator or Brian Balfour's growth loop simulator) contain executable JavaScript generated by an LLM. If rendered carelessly in the user's browser, prompt injections or hallucinations could attempt Cross-Site Scripting (XSS), exfiltrate session credentials from `window.parent.localStorage`, or phone home sensitive startup metrics entered into the calculators.

## Options Considered

### Option A: Direct React DOM Injection / Dangerous Inner HTML
- Render LLM-generated HTML inside the main React app tree using `dangerouslySetInnerHTML`.
- Disastrous security: any script can immediately access session tokens, cookies, and parent DOM APIs.

### Option B: Raw Iframe without sandbox attributes
- Embeds HTML in an `<iframe>`, but with same-origin access intact.
- Flawed security: the iframe shares the host origin (`http://localhost:3000`), allowing full cross-frame DOM inspection.

### Option C: Two-Layer Defense-in-Depth Sandbox (Iframe Null Origin + HTTP Content-Security-Policy)
- **Layer 1 (Vertical Isolation)**: Render within `<iframe sandbox="allow-scripts" src="/api/artifacts/{id}/raw">`. Strictly omit `allow-same-origin`, forcing the browser engine to assign opaque `origin: "null"`. Any attempt to access `window.parent` throws `DOMException: Blocked a frame with origin "null"`.
- **Layer 2 (Horizontal Exfiltration Containment)**: The backend serves `/raw` with a strict `Content-Security-Policy`:
  `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; frame-ancestors 'self' http://localhost:3000;`
  `connect-src 'none'` blocks all outbound network calls (`fetch`, `XMLHttpRequest`, `WebSocket`), preventing calculated metrics from being leaked to external servers.

## Decision
We select **Option C: Two-Layer Defense-in-Depth Sandbox**.

## Why
Guarantees zero parent privilege escalation while completely neutralizing network exfiltration channels, while still allowing rich interactive JavaScript calculators to run client-side.

---

# Decision 011: Fetch ReadableStream SSE Client & Dynamic Split-Pane Architecture

## Context
The frontend needs to support three distinct interaction paradigms in a unified interface:
1. Grounded RAG conversational Q&A (`/api/chat`).
2. Long-form ~1,250-word Ship 30 for 30 essays (`/api/skills/essay`).
3. Interactive HTML/JS tools and calculators (`/api/skills/artifact`).

Native browser `EventSource` is limited to HTTP `GET`, cannot send JSON request bodies (e.g. `session_id`, `topic`, `provider_override`), and risks hitting URL query parameter length limits. Furthermore, rendering both chat and live artifacts in a single column forces users to scroll constantly between conversational bubbles and long artifacts.

## Options Considered

### Option A: Single-column chat with native EventSource via GET query parameters
- Subject to URL length limits and server access log leakage.
- Clutters conversational thread with massive ~1,250-word essays and interactive HTML apps.

### Option B: Fetch API + ReadableStream Reader with Dual Split-Pane Studio Layout
- **Fetch ReadableStream Client**: Use `fetch(url, { method: "POST", body: JSON.stringify(...) })` and decode incoming stream chunks using `response.body.getReader()`. Supports full POST payloads, custom headers, and instant token-by-token rendering.
- **Split-Pane Studio**: Left pane dedicated to conversation, quick prompt chips, and mode switching (`RAG Q&A`, `Ship 30 Essay`, `Interactive Tool`). Right pane dedicated to active artifact rendering (formatted Markdown with word count or sandboxed `<iframe>` with `origin: null` and CSP containment) plus an archive tab of past artifacts.

## Decision
We select **Option B: Fetch API + ReadableStream Reader with Dual Split-Pane Studio Layout**.

## Why
Provides complete control over HTTP POST streaming protocols, eliminates layout thrashing, and creates an exceptional desktop/mobile user experience.

---

# Decision 012: Multi-Stage Standalone Docker Architecture & Host-Gateway Networking

## Context
Production containerization must satisfy three core engineering constraints:
1. Allow single-command reproducible deployment (`docker compose up --build`) across macOS, Linux, and Windows.
2. Allow containerized backend services to communicate with native host Ollama (`llama3.2:3b`) to preserve Apple Silicon Metal GPU acceleration without running Ollama inside a heavy container VM.
3. Keep container image sizes minimal and secure by eliminating build toolchains from runtime images.

## Options Considered

### Option A: Single-stage Dockerfile running npm run dev / pip install in container
- Massive images (>1.5 GB per container).
- Security risk: production image contains compilers, package managers, and devDependencies.
- High memory usage and slow container startup.

### Option B: Multi-Stage Docker Builds with Host-Gateway DNS Alias
- **Next.js Standalone Runner**: Stage 1 installs dependencies; Stage 2 compiles the Next.js standalone server bundle (`output: "standalone"`); Stage 3 (minimal `node:20-alpine`) copies only the standalone server and static assets, reducing image size to ~120 MB.
- **FastAPI Lean Runner**: Stage 1 compiles C-extension wheels (`greenlet`, `asyncpg`); Stage 2 (`python:3.12-slim`) copies pre-built packages and runs non-root Uvicorn.
- **Host Gateway DNS**: In `docker-compose.yml`, configure `extra_hosts: ["host.docker.internal:host-gateway"]` and `OLLAMA_BASE_URL=http://host.docker.internal:11434`. This bridges the container's isolated network loopback to the host Mac's native Ollama instance with zero virtualization overhead.

## Decision
We select **Option B: Multi-Stage Docker Builds with Host-Gateway DNS Alias**.

## Why
Reduces image sizes by ~90%, removes build-tool attack vectors, and unlocks high-speed Metal-accelerated local inference directly from within containerized microservices.

---

# Decision 013: OpenRouter Model Selection (NVIDIA Nemotron 3 Ultra 550B Free Tier)

## Context
For the cloud tier using OpenRouter, users need a high-capacity model suitable for long-form synthesis (e.g. Ship 30 for 30 essays) that does not incur paid API costs during evaluation and development.

## Options Considered

### Option A: Proprietary Paid Tier (`anthropic/claude-3.7-sonnet` or `openai/gpt-4o`)
- High-quality reasoning and writing prose.
- Requires funded credit balance on OpenRouter; fails immediately if the developer or evaluator lacks funded credits.

### Option B: Free-Tier High-Capacity Model (`nvidia/nemotron-3-ultra-550b-a55b:free`)
- 550B parameter class model provided free of charge on OpenRouter.
- Massive parameter capacity for long-form instruction following and deep growth framework synthesis.
- Zero API cost barrier for evaluation and portfolio demonstration.
- Compatible with standard OpenAI `/chat/completions` payload contract.

## Decision
We select **Option B: `nvidia/nemotron-3-ultra-550b-a55b:free`** as the default model for `OPENROUTER_MODEL` and `MODEL_FOR_ESSAY`.

## Why
Enables full long-form essay and artifact generation capabilities via OpenRouter without requiring paid credits, maximizing accessibility while maintaining high inference quality.

## Trade-offs
Free-tier endpoints on OpenRouter can encounter temporary rate limits (HTTP 429) during peak traffic hours. Our `TaskRouter` mitigates this by automatically catching rate limits and cascading down to local Ollama.

---

# Decision 014: Light Liquid Glass Design System Transformation

## Context
The initial frontend utilized a conventional dark-slate developer dashboard aesthetic (`bg-slate-950`). To elevate the product into an Apple/macOS-inspired AI workspace with a calm, tactile spatial environment, a complete visual transformation was required—with zero dark mode, no emojis as UI icons, and a warm orange accent.

## Options Considered

### Option A: Generic Dual-Theme (Dark/Light Switcher)
- Requires maintaining dual CSS variable sets and testing every component under both lighting conditions.
- Often leads to washed-out light mode designs that simply invert background colors without true physical depth.
- Violates the explicit design mandate: "Light mode ONLY. There must be NO dark mode."

### Option B: Dedicated Light Liquid Glass System
- Centralized CSS variable tokens in `:root` with a subtle warm/light canvas background (`radial-gradient` on `#f5f5f3`).
- 4-tiered glass hierarchy (`.glass-subtle`, `.glass`, `.glass-elevated`, `.glass-floating`) utilizing `-webkit-backdrop-filter: blur(...) saturate(...)` with pseudo-element top edge refraction highlights.
- Spatial floating panels with rounded corners (`rounded-2xl` / `rounded-3xl`) and outer workspace margins.
- Warm orange accent (`#f26a21`) strictly reserved for active states, mode pills, primary actions, and focus rings.
- Lightweight SVG pixel cursor (`default`, `pointer`, `text`) for a tactile, retro-modern desktop feel.
- 100% emoji-free UI: replaced all interface emojis with Lucide React icons.

## Decision
We select **Option B: Dedicated Light Liquid Glass System**.

## Why
Delivers a cohesive, high-end spatial workspace that feels like a native macOS application built specifically for AI agents, providing physical depth and calm readability without compromising performance.

## Trade-offs
Backdrop blur can be computationally expensive if applied to hundreds of micro-elements. We mitigate this by applying glass filters exclusively to major spatial surfaces (floating navigation, sidebar, split panes, and input dock) while keeping internal lists and text elements lightweight.





