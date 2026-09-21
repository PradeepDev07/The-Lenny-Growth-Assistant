# Product Requirements Document (PRD)
## The Lenny Growth Assistant

**Status:** Approved  
**Author:** Senior AI Systems Engineer & Technical Team  
**Version:** 1.0.0  
**Target Environment:** Local Machine (Apple Silicon M1 8GB) & Containerized Deployment  

---

## 1. Executive Summary & Problem Statement

Lenny Rachitsky's podcast contains hundreds of hours of high-signal, real-world advice from world-class product leaders, growth practitioners, and startup founders (e.g., Brian Balfour, Elena Verna, Shreyas Doshi). 

However, product managers, founders, and growth leads face three critical friction points:
1. **High Discovery Latency:** Searching for specific tactical frameworks (e.g., "how to build a viral loop vs a paid loop", "activation metric definitions", "0-to-1 PMF indicators") requires scrubbing through multi-hour transcripts.
2. **Hallucination & Lack of Grounding in Generalist LLMs:** Commercial LLMs often provide generic, boilerplate PM advice without citing real practitioner case studies, or hallucinate quotes.
3. **Inability to Execute Offline:** Most modern AI tools depend entirely on proprietary cloud APIs with recurring costs and network requirements, preventing private or offline use.

**The Lenny Growth Assistant** is an agentic, full-stack application that provides:
- Grounded conversational Q&A strictly backed by Lenny's Podcast transcripts with explicit inline citations.
- A dedicated **Ship 30 for 30** essay generation skill that transforms podcast insights into high-impact, skimmable growth essays (~1,250 words).
- Safe, interactive **Artifact Generation** (Markdown & sandboxed HTML) with a split-pane viewer.
- A **Hardware-Conscious Model Router** supporting offline local execution via Ollama (`llama3.2:3b`) alongside cloud providers (Google Gemini & OpenRouter).

---

## 2. Target Personas & Jobs-To-Be-Done (JTBD)

### Target Personas
* **Growth Product Manager:** Needs validated metrics, retention benchmarks, and growth loop mechanics to present to leadership or unblock roadmaps.
* **Early-Stage Founder:** Needs 0-to-1 PMF frameworks, initial pricing strategies, and customer discovery heuristics without reading 40 long transcripts.
* **Content / Growth Marketer:** Needs structured Ship 30 for 30 essays and tactical visual calculators derived from podcast interviews.

### Core Jobs-To-Be-Done
| Persona | Situation | Need | Desired Outcome |
|---|---|---|---|
| Growth PM | Defining onboarding KPIs | Ask tactical question on activation metrics | Cited answer with Elena Verna's exact definitions + timestamp link |
| Founder | Evaluating acquisition channels | Understand loop mechanics vs funnels | Brian Balfour's 3-loop framework distilled into actionable steps |
| Marketer | Preparing a leadership memo | Transform transcript answers into an essay | 1,250-word Ship 30 post ready for distribution |
| Evaluator / Engineer | Running offline demo on 8GB Mac | Toggle offline mode without API keys | Complete end-to-end RAG generation using local Ollama model |

---

## 3. Success Metrics

| Metric | Target | Verification Method |
|---|---|---|
| **Source Citation Accuracy** | ≥ 85% of queries retrieve and cite authentic episode transcripts | Automated retrieval benchmark & manual inspection against curated dataset |
| **Grounded Refusal Rate** | 100% refusal on out-of-domain queries (e.g. quantum physics) | RAG refusal test asserting model states archive does not support the topic |
| **Local Response Latency (p50)** | < 6.0s time-to-first-token on Apple M1 with `llama3.2:3b` | Server-side telemetry logged in `routing_logs` |
| **Cloud Response Latency (p50)** | < 1.5s time-to-first-token on Gemini 2.5 Flash | Server-side telemetry logged in `routing_logs` |
| **Sandbox Security** | 0 cross-origin parent DOM or cookie/token leaks | Automated malicious HTML payload test suite |
| **Local Hardware Safety** | Memory footprint ≤ 4.5 GB total during local generation | Host memory monitoring ensuring zero swap thrashing |

---

## 4. Scope & Boundaries

### In Scope (MVP)
* **Ingestion Pipeline:** Semantic chunking (~500 tokens, 10% overlap), metadata extraction (`episode_id`, `guest`, `title`, `url`, `date`), and vector embedding generation.
* **Dual Persistence Layer:** SQLite for lightweight zero-config local development; PostgreSQL + pgvector for Docker deployment.
* **Model Router & Fallback Chain:**
  * Intent Routing: Fast classification.
  * Retrieval QA: Gemini 2.5 Flash / OpenRouter / Ollama fallback.
  * Essay Generation: High-capability model / Ollama fallback.
  * Artifact Generation: Structured code generation.
* **Grounded RAG Assistant:** Conversation history, context assembly, source citation injection (`[Lenny Podcast — Guest — Episode Title]`).
* **Ship 30 for 30 Skill:** Deterministic ~1,250-word essay generation with Hook, Narrative, Evidence, Framework, Application, and Takeaways.
* **Safe Artifact Viewer:** Split-pane layout with `<iframe sandbox="allow-scripts">` (no `allow-same-origin`) and native Markdown viewer.
* **Observability & Diagnostics:** `/health` and `/config` endpoints with structured JSON logging and routing telemetry.

### Out of Scope (Non-Goals)
* Multi-tenant authentication / user logins (Single-user workspace suitable for local assessment).
* Full podcast audio transcription / scraping (curated high-signal transcript corpus provided).
* Fine-tuning custom LLMs.
* Paid billing / subscription management.

---

## 5. Technical Architecture & Constraints

### Hardware Constraint
* **Development Machine:** Apple MacBook Air M1 with 8 GB Unified RAM and 23 GiB available disk.
* **Implication:** The local tier **must not** run models larger than 3B parameters. `llama3.2:3b` is designated as the primary local Ollama model.

### Provider Matrix & Fallback Order
| Task | Primary Tier | Secondary Tier | Local Offline Fallback |
|---|---|---|---|
| `retrieval_qa` | Google Gemini 2.5 Flash | OpenRouter (`openrouter/free`) | Ollama (`llama3.2:3b`) |
| `essay_generation` | OpenRouter (`openrouter/free`) | Google Gemini 2.5 Flash | Ollama (`llama3.2:3b`) |
| `artifact_generation` | Google Gemini 2.5 Flash | OpenRouter (`openrouter/free`) | Ollama (`llama3.2:3b`) |
| `intent_routing` | Rule-based / Gemini Flash Lite | Ollama (`llama3.2:3b`) | Deterministic regex fallback |

---

## 6. Security & Threat Model

1. **Untrusted Code Execution (HTML Artifacts):**
   * *Threat:* Malicious HTML payload trying to read parent auth tokens, access `window.parent.document`, or exfiltrate local data.
   * *Mitigation:* Sandboxed `<iframe>` strictly with `sandbox="allow-scripts"`. Omitting `allow-same-origin` guarantees `null` origin, making cross-window DOM access physically prohibited by the browser engine.
2. **Prompt Injection:**
   * *Threat:* User prompt attempting to override system instructions or bypass grounding to generate fabricated quotes.
   * *Mitigation:* Explicit delimiter boundaries between system prompt, retrieved transcript context, and user query. Explicit instruction: *"Only answer using the provided transcript excerpts. If the excerpts do not contain the answer, state that the archive does not contain sufficient information."*
3. **API Key Security:**
   * *Threat:* Cloud provider credentials leaking to the frontend.
   * *Mitigation:* All LLM calls and API keys live exclusively in the FastAPI backend environment. The client only receives SSE token streams.

---

## 7. Delivery Milestones

1. **Phase 0-1:** Scaffolding, Environment Discovery, and PRD (Completed).
2. **Phase 2:** Minimal FastAPI backend with `/health` and `/config` diagnostics.
3. **Phase 3:** Persistence layer (Sessions, Messages, Artifacts, Routing Logs) with SQLite/Postgres compatibility.
4. **Phase 4 & 4.5:** Multi-provider LLM Layer (Ollama, Gemini, OpenRouter) and Task Router.
5. **Phase 5:** Transcript Ingestion, Semantic Chunking, and Vector Search Engine.
6. **Phase 6:** Grounded RAG Chat Engine with Streaming SSE and Source Attribution.
7. **Phase 7:** Ship 30 for 30 Essay Skill Engine.
8. **Phase 8:** Sandboxed Artifact Generation & Security Verification.
9. **Phase 9:** Next.js Full-Stack Frontend with Split-Pane Artifact Viewer.
10. **Phase 10-12:** Observability, Resilience, Docker Compose, and Consolidated Test Suite.
