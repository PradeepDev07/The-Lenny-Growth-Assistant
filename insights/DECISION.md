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
Scattered direct SDK calls were rejected because they prevent automated fallback and make unit testing impossible.
