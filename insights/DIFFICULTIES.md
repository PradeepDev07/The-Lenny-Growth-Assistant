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
