# The Lenny Growth Assistant — Demo Walkthrough (walkthrough_demo.md)

> **Document Purpose:** Presentation-friendly, step-by-step demonstration walkthrough guide for evaluators, hiring managers, and technical leads. Use this document when conducting a live screen-share or architectural review of **The Lenny Growth Assistant**.

---

## 1. Introduction

**The Lenny Growth Assistant** is an end-to-end full-stack AI system designed to deliver verified, citation-grounded product and growth advice. It combines retrieval-augmented generation (RAG) over Lenny's Podcast transcripts with long-form essay compilation (Ship 30 for 30 methodology) and client-side interactive calculators (sandboxed single-file HTML/JS applications).

The system was engineered with two foundational principles:
1. **Zero Tolerance for Hallucination:** The model is bound by a strict XML grounding contract and similarity score thresholds. If an answer cannot be grounded directly in transcript evidence, it deterministically refuses.
2. **Hardware-Conscious Dual Topology:** It can run 100% offline on an 8 GB unified memory Apple Silicon Mac using local Ollama (`llama3.2:3b`) without memory swapping or GPU thrashing, while seamlessly cascading to high-throughput cloud models (Google Gemini 2.5 Flash and OpenRouter) in production.

---

## 2. Problem

Product managers, startup founders, and growth practitioners operate in high-stakes environments where generic AI advice is dangerous:
- Public LLMs output vague, unverified platitudes when asked complex strategic questions (e.g., how to benchmark retention, construct viral loops, or design freemium tiers).
- The world's top growth frameworks exist inside **Lenny's Podcast**, where legendary practitioners (Elena Verna, Brian Balfour, Shreyas Doshi, Sean Ellis) share exact formulas and tactical playbooks.
- However, hundreds of hours of conversational audio are unindexed, unsearchable by concept, and impractical to consult during daily product work.
- Turning conversational dialogue into executive memos or interactive models typically takes hours of manual synthesis.

---

## 3. User Journey

```text
User opens https://lennygrowth.pradeepleadsystems.in
        ↓
Sees Light Liquid Glass Studio with active service health status
        ↓
Selects interaction mode: "RAG Q&A", "Ship 30 Essay", or "Interactive Tool"
        ↓
Submits query (or clicks a curated quick-prompt chip)
        ↓
Instant token streaming begins over Server-Sent Events (<200ms latency)
        ↓
Inline citation cards appear: [Lenny Podcast — Guest Name — Episode Title]
        ↓
If essay or interactive tool: full artifact renders in right-hand studio pane
        ↓
User interacts with live calculator sliders or copies formatted .md essay
        ↓
User asks contextual follow-up; conversation history maintains thread continuity
```

---

## 4. Product Demo: Step-by-Step UI Walkthrough

### Step 1: Landing & Health Verification
1. Navigate to: **`https://lennygrowth.pradeepleadsystems.in`**.
2. Point out the top header bar:
   - System title and active session badge.
   - Live service health pills showing database and cloud inference readiness.
   - Ambient Light Liquid Glass aesthetic: subtle canvas gradient, translucent glass elevation, and warm orange active accents.

### Step 2: Grounded Conversational RAG
1. Click the quick prompt: **"Brian Balfour: Growth Loops"**.
2. **Observe:**
   - Immediate token-by-token streaming over Server-Sent Events.
   - The assistant breaks down qualitative loops vs. traditional funnels.
   - At the bottom of the response, citation cards render with guest name, episode title, and direct source link.
3. Ask an out-of-domain query: *"How do I bake an authentic sourdough loaf?"*
4. **Observe Anti-Hallucination Refusal:**
   - The assistant immediately replies: *"I searched Lenny's Podcast transcripts, but this topic is not covered in the archive."*
   - Zero hallucination from pre-trained weights.

### Step 3: Ship 30 for 30 Long-Form Essay Skill
1. In the chat input dock, click the mode selector and switch to **"Ship 30 Essay"**.
2. Enter topic: **"Elena Verna: PLG Activation Loops"**.
3. **Observe:**
   - The system streams a structured ~1,250-word digital essay into the right-hand **Artifact Studio**.
   - Note the rigid 6-stage compositional structure:
     1. The Hook (1 contrarian sentence).
     2. The 1-3-1 Cadence rhythm.
     3. The PM/Founder Observed Narrative.
     4. The Core Framework Breakdown (bulleted with inline citations).
     5. Practical Application: 3 Actionable Takeaways for Monday morning.
     6. The Anchor Conclusion.
   - Inspect the toolbar in the artifact pane: word count badge (~1,250 words), segmented switcher between raw `.md Format` (with line numbers) and rich rendered preview, one-click copy, and file download.

### Step 4: Sandboxed Interactive Calculator Tool
1. Switch the mode selector to **"Interactive Tool"**.
2. Enter topic: **"Compounding Growth Loop Simulator"**.
3. **Observe:**
   - The assistant streams a complete, standalone single-file HTML/CSS/JS web application.
   - The right pane automatically mounts the live application inside a sandboxed iframe.
   - Adjust input sliders (Acquisition Volume, Conversion Rate, Cycle Time in Days).
   - Watch output KPI cards and visual growth curves react reactively in real time.
4. Point out the security banner:
   - `Sandboxed Iframe (origin: null | CSP: connect-src 'none')`.
   - Explain that the tool cannot touch parent cookies, local storage, or exfiltrate private metrics to external servers.

---

## 5. Architecture

```text
┌────────────────────────────────────────────────────────┐
│ Next.js 14 Frontend Studio (Port 3000 / Production URL)│
└───────────────────────────┬────────────────────────────┘
                            │ Fetch API (POST) / SSE Stream
                            ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI Application Gateway (Port 8000)                │
│ • CORS Middleware & Standardized Error Handlers        │
│ • /api/chat, /api/sessions, /api/skills                │
└───────┬───────────────────┬────────────────────┬───────┘
        │                   │                    │
        ▼                   ▼                    ▼
┌──────────────┐    ┌───────────────┐    ┌───────────────┐
│ PostgreSQL / │    │ Boosted BM25  │    │ TaskRouter &  │
│ SQLite ORM   │    │ Vector Store  │    │ Provider Adap.│
│ (Sessions,   │    │ (Guest 2.5x,  │    │ (Gemini Flash,│
│  Messages,   │    │  Title 1.8x,  │    │  OpenRouter,  │
│  Artifacts)  │    │  Coverage)    │    │  Ollama 3B)   │
└──────────────┘    └───────────────┘    └───────────────┘
```

---

## 6. RAG Walkthrough

```text
Documents (Raw Podcast Audio Transcripts)
       ↓
Dialogue Chunker (~1200 characters, 200 char sliding overlap, speaker boundaries)
       ↓
Document Store (JSON cache with metadata tags: guest, episode_id, title, url)
       ↓
User Query Submitted
       ↓
Lexical Search with Term Coverage Guard & Field Boosts (Guest 2.5x, Title 1.8x)
       ↓
Similarity Threshold Evaluation (score >= 0.05)
       ↓
Grounded Context Injection into <transcript_evidence> XML Delimiters
       ↓
LLM Generation via Streaming SSE
       ↓
Grounded Response with Verified Attribution Cards
```

---

## 7. LLM Provider Architecture

The project implements the **Adapter Pattern** through `BaseLLMProvider`:
- **Local Development / Offline Mode:** Uses `OllamaProvider` connecting to `http://localhost:11434` with `llama3.2:3b`. Generates ~30 tokens/sec on Apple Silicon Metal acceleration with zero cloud costs.
- **Production Mode:** Uses `GeminiProvider` (`gemini-2.5-flash`) for low-latency RAG and code synthesis, and `OpenRouterProvider` (`nvidia/nemotron-3-ultra-550b-a55b:free`) for long-form essay generation.
- **Automated Cascading Fallback:** If a cloud provider hits rate limits (HTTP 429) or network timeouts, `TaskRouter` catches the exception and cascades down the fallback chain to the next available tier without crashing the user session.

---

## 8. Source Grounding

Every answer is anchored directly to transcript evidence through a multi-tier defense:
1. **XML Isolation Delimiters:** `<transcript_evidence>` blocks isolate source facts from the user's `<user_question>`.
2. **Authority Hierarchy:** System instructions declare that `<user_question>` has zero authority to redefine operating rules, preventing prompt injections.
3. **Structured Attribution Format:** The model is bound to cite claims inline using `[Lenny Podcast — Guest Name — Episode Title]`.
4. **Structured JSON Telemetry:** On stream completion, the backend emits clean metadata dictionaries containing episode titles, guest names, source URLs, and relevance scores.

---

## 9. Artifact Generation

The platform supports two distinct artifact classes:
1. **Markdown Digital Essays (`type="markdown"`):**
   - Built for reading, distribution, and export.
   - Enforces Ship 30 for 30 atomic structure (~1,250 words).
   - Displayed in the studio pane with live word counts, line-numbered raw view, and one-click markdown export.
2. **Interactive Applications (`type="html"`):**
   - Single-file HTML5/CSS/JavaScript tools.
   - Standalone execution with zero CDN dependencies.
   - Protected by two-layer defense-in-depth isolation:
     - Vertical Isolation: `<iframe sandbox="allow-scripts">` without `allow-same-origin` sets `origin: null`.
     - Horizontal Containment: `Content-Security-Policy: connect-src 'none'` blocks all outbound network calls.

---

## 10. Deployment

- **Public Production URL:** `https://lennygrowth.pradeepleadsystems.in`
- **Frontend Stack:** Next.js 14 standalone container.
- **Backend Stack:** FastAPI container running with Uvicorn.
- **Persistence:** Relational database with automatic startup table initialization via SQLAlchemy.
- **Networking & SSL:** HTTPS termination with parameterized CORS headers authorizing cross-origin API requests.

---

## 11. Live Demo Checklist

| Step | Action | Expected Output | Status |
| :--- | :--- | :--- | :--- |
| **1** | Open `https://lennygrowth.pradeepleadsystems.in` | Application loads smoothly with green health indicators. | PASS |
| **2** | Create a new session | Clean conversation workspace opens. | PASS |
| **3** | Submit prompt: *"Brian Balfour: Growth Loops"* | Instant SSE streaming with inline citations. | PASS |
| **4** | Submit out-of-domain prompt: *"Bake sourdough bread"* | Model states topic not covered in podcast archive. | PASS |
| **5** | Switch to *"Ship 30 Essay"* mode | Generates ~1,250-word essay in right-hand studio pane. | PASS |
| **6** | Switch to *"Interactive Tool"* mode | Generates functional reactive calculator in sandboxed iframe. | PASS |
| **7** | Refresh page | Session history, messages, and artifacts persist reliably. | PASS |
