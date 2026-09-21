# Real Engineering Difficulties & Investigation Log (DIFFICULTIES.md)

This document records real engineering problems, unexpected observations, root-cause investigations, failed attempts, fixes, and lessons learned.

---

## Observation 001 — Hardware RAM Constraint vs Reference Document Recommendations

### Symptom
The reference guide suggests pulling `llama3.1:8b` as the default local Ollama model.
During Phase 0 hardware discovery, host inspection revealed:
- Host: Apple MacBook Air M1.
- Total Unified RAM: 8 GB.
- Free Disk Space: 23 GiB.
- Docker daemon: Inactive / not running (`dial unix /Users/macki/.docker/run/docker.sock: connect: no such file or directory`).

### Expected
Smooth local development without machine freeze or swap thrashing.

### Investigation
- An 8B parameter model at 4-bit quantization consumes approximately 4.8 GB - 5.2 GB of memory in Ollama.
- macOS itself requires ~2.5 GB.
- If Docker Desktop runs on macOS, its Linux VM by default claims 2 GB - 4 GB of RAM.
- Launching Next.js (Node.js) + FastAPI (Python Uvicorn) + PostgreSQL (Docker) + Ollama (8B model) would require ~10 GB - 12 GB of RAM on an 8 GB physical machine, immediately causing the macOS kernel to thrash swap onto the SSD, leading to high latency and system unresponsiveness.

### Root Cause
Unified memory architecture means CPU, GPU, and all operating system processes compete for the same 8 GB pool. Heavy model weights occupy non-pageable memory.

### Failed Attempts / Rejected Naive Paths
- Attempting to load an 8B model would cause either Ollama runner crashes or severe Mac slowdowns.

### Fix
1. Calibrate the local baseline model to `llama3.2:3b` (~2.0 GB footprint) or `llama3.2:1b` (~1.3 GB).
2. Allow dual persistence: SQLite for lightweight, instant, zero-docker local development, while maintaining full PostgreSQL / pgvector compatibility for Docker Compose environments.

### Verification
- Checked memory headroom calculations: macOS (2.5 GB) + Ollama 3B (2.0 GB) + Python Uvicorn (150 MB) + Node/Next (250 MB) = ~4.9 GB, safely within the 8 GB limit with ~3 GB buffer for OS cache and browser tabs.

### Lesson
Never blindly assume reference documentation hardware recommendations match the actual physical deployment host. Real software engineering requires matching the architecture to physical hardware boundaries.

---

## Problem 002 — Python 3.12 SQLAlchemy Async Engine Missing `greenlet`

### Symptom
When running `pytest` with `async_engine`, SQLAlchemy threw:
`ValueError: the greenlet library is required to use this function. No module named 'greenlet'`.

### Expected
Smooth async connection using `create_async_engine`.

### Root Cause
SQLAlchemy's async wrapper bridges Python's async/await event loop with its internal synchronous core using `greenlet`. In Python 3.12, `greenlet` is not bundled by default and must be explicitly installed.

### Fix
Added `greenlet>=3.0.3` to `backend/requirements.txt` and installed it.

### Lesson
Async ORM layers often require low-level coroutine switching C-extensions (`greenlet`). Always ensure this dependency is explicitly pinned for Python 3.12 environments.

---

## Problem 003 — SQLite Default Foreign Key Inactivity Breaking Cascade Deletion

### Symptom
In relational unit tests, deleting a parent session could leave behind child messages in SQLite if FK enforcement is inactive.

### Root Cause
For backwards compatibility with 1990s databases, SQLite defaults `PRAGMA foreign_keys = OFF` on every new connection. Unless an explicit pragma is run per connection, SQLite completely ignores `ON DELETE CASCADE`.

### Fix
Attached an event listener `@event.listens_for(engine.sync_engine, "connect")` in `backend/app/db/session.py` that executes `PRAGMA foreign_keys=ON` whenever a SQLite connection is established.

### Verification
`test_sessions.py` asserts that directly querying the `messages` table after deleting a session returns 0 rows.

### Lesson
Never assume SQLite behaves like PostgreSQL out of the box. Explicit pragma initialization is mandatory for relational integrity in SQLite.

---

## Problem 004 — Lexical Flukes & Stopword Inflation in Retrieval Unit Tests

### Symptom
When running `test_similarity_threshold_rejects_unrelated_queries`, the unrelated query `"how to change the transmission fluid on a 1998 honda civic"` returned 2 chunks from Brian Balfour's episode instead of returning `[]`.

### Expected
Out-of-domain automotive queries should score below the threshold and return an empty list.

### Investigation
- The transcript contains the sentence: *"Lenny: And how do Growth Loops change this dynamic?"*
- Because the word `"change"` was only in 2 chunks, its Inverse Document Frequency (IDF) was high (~1.48).
- Naive BM25 awarded ~0.7 score simply because `"change"` matched, despite 5 other critical query terms (`transmission`, `fluid`, `1998`, `honda`, `civic`) having zero presence in the document (query term coverage of only 16%).

### Fix
Implemented a dual safeguard in `backend/app/retrieval/vector_store.py`:
1. Comprehensive English stopword filtering (`STOPWORDS`).
2. Query Term Coverage Guard: for queries with 3+ content terms, a chunk must match at least 2 distinct content terms. If coverage is below this threshold, the score is forced to `0.0`.

### Verification
Reran pytest: all authentic queries (Brian Balfour, Elena Verna, Shreyas Doshi, Lenny) maintained 100% top-rank precision, while all unrelated queries (quantum mechanics, brownies, car maintenance) returned strictly 0 chunks (`[]`).

### Lesson
Lexical keyword search without query term coverage guards is prone to single-word accidental matches. Enforcing minimum term coverage for multi-word queries eliminates spurious false-positive retrievals.


