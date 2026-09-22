# My Understanding of the System (MY_UNDERSTANDING.md)

This document tracks the user's mental model, key architectural lessons learned, verified concepts, and evolving mastery of the system.

---

## System Overview
The Lenny Growth Assistant is a full-stack, AI-powered system that delivers answers to startup and product growth questions, grounded in transcripts from Lenny's Podcast. It features:
1. Grounded RAG conversational Q&A with explicit inline source citations.
2. Ship 30 for 30 essay generation skill with tight structural constraints.
3. Safe artifact generation (Markdown and sandboxed HTML).
4. Multi-provider LLM routing: local Ollama for offline demo, Google Gemini for large-context RAG, and OpenRouter for multi-model access.

---

## Request Lifecycle & Data Flow

```
1. Client POST /api/chat (session_id, message)
   ↓
2. Backend validates request & retrieves recent session history (Relational DB)
   ↓
3. Intent Router classifies prompt (QA / Essay / Artifact)
   ↓
4. If QA or Essay:
   Query Embedding → Vector Store ANN Search → Top-k Transcript Chunks
   ↓
5. Grounding Prompt Assembly (System prompt + Retrieved Chunks + History + Query)
   ↓
6. Task Router selects Provider (Cloud Gemini / OpenRouter → Local Ollama fallback)
   ↓
7. LLM streams tokens back via Server-Sent Events (text/event-stream)
   ↓
8. Client renders text / extracts Artifact into sandboxed <iframe> (origin null)
   ↓
9. Backend persists user message, assistant response, source citations, & telemetry
```

## Backend Architecture
- Framework: FastAPI (Python 3.12).
- Key responsibilities: API routing, session management, vector search retrieval, prompt assembly, LLM provider orchestration, and streaming response delivery (via SSE).

## Database & Persistence
- Schema entities: `sessions`, `messages`, `artifacts`, `routing_logs`.
- Dual database support: Seamless transition between lightweight embedded SQLite (zero-overhead local testing) and PostgreSQL with `pgvector` (production containerized stack).
- **Core Principle:** Strict separation between transactional conversation history (deterministic lookups) and transcript embeddings (similarity search).

## RAG Pipeline
- Transcript ingestion -> Semantic chunking (~500 tokens with overlap) -> Dense vector embedding -> Storage & Indexing -> Vector similarity retrieval -> Grounded prompt construction -> Constrained generation -> Source attribution.

## LLM Provider Layer & Router
- Provider abstraction (`BaseLLMProvider`) decoupling business logic from vendor SDKs.
- Task-based routing: Intent Routing, Retrieval QA, Essay Writing, Artifact Generation.
- Cascading fallback: Primary cloud -> Secondary cloud -> Local Ollama fallback (`llama3.2:3b`).

## Artifact System & Security
- Two artifact modes: native Markdown and sandboxed HTML.
- Defense-in-depth security model: Sandboxed `<iframe>` with `sandbox="allow-scripts"` (strictly omitting `allow-same-origin`), assigning an opaque `origin: "null"` that blocks access to `window.parent`, cookies, local storage, and DOM.

## Verified Mental Models
- **Memory & Apple Silicon:** Unified memory means memory is shared across GPU, OS, Docker, and apps. An 8B model requires 4.8GB+ RAM, causing swap thrashing on an 8GB machine. Targeting `llama3.2:3b` (~2.0 GB) guarantees smooth performance and 25-35 t/s generation.
- **Relational vs Vector Separation:** Relational DBs store user-specific transactional data (`WHERE session_id = ?`). Vector stores hold static shared reference knowledge (`embedding <=> query`). Mixing them pollutes the vector index.
- **Cascade Deletion & Referential Integrity:** Relational foreign keys ensure that child records (messages, artifacts) do not become orphaned when parent entities (sessions) are deleted. Configuring `cascade="all, delete-orphan"` coupled with `PRAGMA foreign_keys=ON` guarantees atomic cleanup.
- **Session Isolation & Context Window Preservation:** Scoping queries strictly to `WHERE session_id = :session_id` prevents prompt cross-contamination between unrelated chats and maximizes available token space for retrieved podcast transcript chunks.
- **Provider Adapter Normalization:** Normalizing vendor responses into a single `LLMResponse` contract protects upstream business logic, databases, and UI from API drift when switching between Gemini, OpenRouter, and Ollama.
- **Server-Side Execution vs Browser Mixed-Content:** The client browser strictly communicates via HTTPS with the FastAPI backend. All local Ollama calls execute server-side on localhost or private Docker virtual networks, avoiding browser mixed-content blocks entirely.
- **B-Tree vs Vector Space Indexing:** Relational B-Trees index 1-dimensional scalar values for exact matches ($O(\log N)$). Dense vector embeddings map concepts into high-dimensional space where semantic closeness is measured geometrically via angles (Cosine Similarity) or graph traversals (HNSW).
- **The Similarity Threshold Goldilocks Zone:** Setting the threshold too low (`0.0`) stuffs irrelevant context and induces hallucinations. Setting it too high (`0.98`) causes catastrophic over-refusal because natural language questions rarely match transcript text verbatim. Calibrated thresholds (`~0.45 – 0.55`) cleanly separate relevant evidence from out-of-domain queries.
- **Iframe Sandbox Defense:** `sandbox="allow-scripts"` permits client-side interactivity (calculators, charts), while omitting `allow-same-origin` sets `origin: null`, triggering browser `SecurityError` if scripts attempt cross-frame parent DOM or storage access.
- **Prompt Delimiter Boundaries & Authority Hierarchy:** Wrapping retrieved reference text in `<transcript_evidence>` and user prompts in `<user_question>` establishes explicit cognitive isolation. Instructing the model that `<user_question>` has zero authority to modify system constraints prevents prompt injection and guarantees grounded refusal when evidence is absent.
- **Progressive Disclosure in Streaming SSE:** Streaming tokens immediately via SSE delivers perceived zero-latency responsiveness, while deferring citation badges and telemetry until stream termination (`{"event": "done"}`) eliminates layout shifts during reading.
- **Structural Scaffolding & Autoregressive Pacing:** Autoregressive transformers predict next tokens without internal word counters or lookahead planning. Breaking prompts into sequential milestones (Hook → 1-3-1 → Narrative → Framework → Takeaways) converts long-form synthesis into discrete sub-goals, preventing small local models from prematurely terminating generation.
- **Task-Based Hardware Tradeoffs:** Interactive chat (~200 tokens) is optimal for local edge compute (`llama3.2:3b` at 30 t/s delivers private 5s responses). Long-form synthesis (~1,800 tokens) risks sustained 70s GPU thrashing and memory growth on an 8GB host, making cloud routing with local offline fallback the ideal balance.
- **Two-Way Defense-in-Depth Sandbox:** Sandboxing requires a two-way perimeter: `sandbox="allow-scripts"` omitting `allow-same-origin` sets `origin: null` to block inward vertical privilege escalation to `window.parent`, while `Content-Security-Policy: connect-src 'none'; img-src data:;` blocks outward horizontal network exfiltration of sensitive metrics.
- **Fetch ReadableStream vs Native EventSource:** Native browser `EventSource` is strictly restricted to HTTP `GET`, cannot send JSON request bodies, and does not support custom headers. Using `fetch()` with `ReadableStream` (`response.body.getReader()`) unlocks full `POST` request flexibility with real-time byte-by-byte token streaming.
- **Rigid Viewport Sandboxing:** Because cross-origin security prevents a parent container from reading `iframe.contentDocument.body.scrollHeight`, sandboxed frames must be rendered in fixed viewports (`h-full w-full`) with internal scrolling rather than attempting dynamic height calculation.
- **Host-to-Container Network Bridging:** A Docker container's `localhost` loopback is isolated to the container. To reach native services running on the physical host (like Ollama with Metal GPU acceleration), the container must connect through `host.docker.internal` via Docker's host-gateway DNS alias.
- **Multi-Stage Docker Builds:** Separating the build environment (heavy compilers, npm devDependencies) from the production runner (minimal Alpine/Debian slim base) shrinks image sizes by ~90% and eliminates CVE attack surface.




