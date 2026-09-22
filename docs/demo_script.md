# Video Demo Presentation Script (demo_script.md)

**Target Duration:** 2.5 to 3.0 minutes  
**Audience:** Technical Hiring Manager, AI Systems Reviewer, or Senior Engineering Mentor  

---

### [0:00 – 0:30] The Hook & Problem Statement

> *"Hi everyone. Product and growth advice online is noisy, ungrounded, and full of generic AI hallucinations. Today, I'm excited to present **The Lenny Growth Assistant**—a full-stack, hardware-conscious AI advisory studio grounded exclusively in authentic **Lenny's Podcast** transcripts."*
>
> *(Show browser on `http://localhost:3000` with the split-pane UI. Point out the live health indicators in the top bar: Database: Green, Local Ollama 3B: Green, Cloud LLM: Green.)*
>
> *"We designed this system under a strict constraint: it must run completely offline on an 8 GB unified memory M1 MacBook Air using local Ollama (`llama3.2:3b`) without swap thrashing, while seamlessly cascading to cloud models when configured."*

---

### [0:30 – 1:15] Feature 1 & 2: Grounded RAG Chat & Anti-Hallucination Refusal

> *(Click the quick prompt: **"Brian Balfour: Growth Loops"**)*
>
> *"Notice what happens as I send this query. Over Server-Sent Events, the assistant streams tokens immediately using the Fetch API with `response.body.getReader()`. Every single claim is attributed inline with an authentic citation card: `[Lenny Podcast — Brian Balfour — Growth Loops and Retention Mechanics]`."*
>
> *(Type an out-of-domain test query: **"How do I bake a sourdough loaf with wild yeast?"**)*
>
> *"Now watch our anti-hallucination defense. In our system prompt, retrieved excerpts are strictly delimited inside `<transcript_evidence>` blocks. Because sourdough is not in Lenny's podcast archive, our BM25 vector engine returns an empty result, and the assistant immediately and respectfully refuses: 'I searched Lenny's Podcast transcripts, but this topic is not covered in the archive.' Zero hallucination."*

---

### [1:15 – 1:55] Feature 3: Ship 30 for 30 Essay Generation

> *(Switch the mode selector in the chat pane to **"Ship 30 Essay"** and type: **"Elena Verna PLG Activation Loops"**)*
>
> *"Next is our **Ship 30 for 30** essay skill engine. Transforming podcast conversations into high-impact digital writing requires strict structural scaffolding to prevent small models from collapsing into brief 200-word summaries.*
>
> *Here, our 6-stage compositional compiler enforces: a 1-sentence contrarian Hook, a 1-3-1 cadence rhythm, an observed PM narrative, Elena Verna's core activation framework with inline citations, and 3 actionable takeaways for Monday morning.*
>
> *Notice how the finished essay automatically docks in our right-hand studio pane, displaying an exact word count (~1,250 words) with one-click Markdown copying and export."*

---

### [1:55 – 2:35] Feature 4: Sandboxed Interactive Calculators & CSP Security

> *(Switch the mode selector to **"Interactive Tool"** and type: **"Growth Loop Compounding Simulator"**)*
>
> *"Finally, reading a framework is good, but interacting with the numbers drives executive decisions. Here, the assistant generates a standalone, single-file HTML/JS reactive compounding calculator.*
>
> *Look closely at how this is rendered. LLM-generated JavaScript presents a serious security risk if uncontained. We implemented a two-layer defense-in-depth perimeter:*
> 1. *Vertical Isolation: The calculator runs inside an `<iframe>` with `sandbox="allow-scripts"` omitting `allow-same-origin`, assigning it an opaque `origin: "null"`. Any attempt to inspect the parent app or steal session tokens throws a browser `SecurityError`.*
> 2. *Horizontal Containment: The backend serves the raw HTML with a strict `Content-Security-Policy: connect-src 'none'; default-src 'none'; img-src data:;`. This physically blocks the iframe from exfiltrating sensitive calculation metrics to external attacker servers.*
>
> *Users can adjust inputs, cycle lengths, and retention rates in real-time with zero security exposure."*

---

### [2:35 – 3:00] Conclusion, Docker Orchestration & Verification

> *(Switch to terminal or point to `docker-compose.yml` and test suite)*
>
> *"Under the hood:*
> - *The whole stack runs in one command via `docker compose up --build` with PostgreSQL and multi-stage Next.js/FastAPI builds.*
> - *Our automated test suite has 33 passing tests covering all prompt delimiters, vector thresholds, cascade deletions, and CSP headers.*
>
> *Thank you for watching!"*
