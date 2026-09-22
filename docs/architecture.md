# System Architecture Specification (architecture.md)

## 1. Executive Summary

**The Lenny Growth Assistant** is an end-to-end full-stack AI system designed to deliver verified, citation-grounded product and growth advice. It combines retrieval-augmented generation (RAG) over Lenny's Podcast transcripts with long-form essay compilation (Ship 30 for 30) and client-side interactive calculators (sandboxed HTML/JS apps).

---

## 2. Component Diagram

```mermaid
graph TD
    Client["Next.js 14 Frontend Studio (:3000)"]
    API["FastAPI Gateway (:8000)"]
    
    subgraph Core_Services ["FastAPI Backend Services"]
        Router["TaskRouter (Priority & Fallback Chains)"]
        RAG["RAG Engine (XML Grounding)"]
        Ship30["Ship 30 Skill Engine"]
        InteractiveSkill["Interactive Artifact Engine"]
        Retriever["BM25 Vector Store (Guest Boost + Coverage Guard)"]
        Repo["SQLAlchemy Repository Layer"]
    end
    
    subgraph Downstream_Inference ["Inference Providers"]
        Ollama["Local Ollama (llama3.2:3b)"]
        Gemini["Google Gemini 2.0 Flash"]
        OpenRouter["OpenRouter (Claude / GPT)"]
    end

    subgraph Persistence ["Data Layer"]
        Postgres[("PostgreSQL 16 + pgvector / SQLite")]
        VectorCache[("vector_cache.json")]
    end

    Client -->|SSE Stream: /api/chat| API
    Client -->|SSE Stream: /api/skills/essay| API
    Client -->|SSE Stream: /api/skills/artifact| API
    Client -->|Iframe Embed: /api/artifacts/:id/raw| API

    API --> RAG
    API --> Ship30
    API --> InteractiveSkill

    RAG --> Retriever
    Ship30 --> Retriever
    InteractiveSkill --> Retriever

    Retriever --> VectorCache

    RAG --> Router
    Ship30 --> Router
    InteractiveSkill --> Router

    Router --> Ollama
    Router --> Gemini
    Router --> OpenRouter

    RAG --> Repo
    Ship30 --> Repo
    InteractiveSkill --> Repo
    Repo --> Postgres
```

---

## 3. Data Flow & Sequence Diagrams

### 3.1 Conversational RAG SSE Stream

```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant API as FastAPI Router
    participant DB as Repository (SQLite / Postgres)
    participant VS as BM25 Vector Store
    participant Router as TaskRouter
    participant LLM as Provider (Ollama / Gemini)

    User->>API: POST /api/chat {session_id, message, provider_override?}
    API->>DB: Verify session exists (404 if missing)
    API->>DB: Persist user message immediately
    API->>VS: search(message, top_k=3, min_score=0.05)
    VS-->>API: Return grounded chunks with guest/episode metadata
    API->>API: Compile XML prompt (<transcript_evidence> + <user_question>)
    API->>Router: get_streaming_provider("retrieval_qa")
    Router-->>API: Active provider instance
    API-->>User: HTTP 200 StreamingResponse (text/event-stream)
    
    loop Stream Tokens
        LLM-->>API: Yield token chunk
        API-->>User: data: {"token": "..."}\n\n
    end

    API->>DB: Persist assistant message with sources & latency
    API->>DB: Log routing telemetry (model, provider, latency, fallback_used)
    API-->>User: data: {"event": "done", "sources": [...], "model_info": {...}}\n\n
```

---

## 4. Grounded Vector Retrieval Architecture

1. **Dialogue Chunking (`ingestion/chunker.py`)**:
   - Chunks transcripts at speaker turn boundaries (~1,200 characters) with a 200-character sliding overlap.
   - Preserves metadata tags on every chunk: `guest`, `source_title`, `url`, `chunk_index`.

2. **Boosted Lexical BM25 Engine (`backend/app/retrieval/vector_store.py`)**:
   - **Guest Weight Boosting (2.5x)**: When a query mentions a guest name (e.g. "Elena Verna" or "Brian Balfour"), chunks with matching guest names receive a 2.5x multiplier.
   - **Episode Title Boosting (1.8x)**: Chunks with relevant keywords in the title receive an extra 1.8x weight.
   - **English Stopword Removal**: Filters out common words ("the", "is", "at", "which", "on") to eliminate lexical noise.
   - **Query Term Coverage Guard**: For multi-word queries (≥3 content terms), a chunk is discarded unless it matches at least 2 distinct search terms. This strictly prevents common verbs from matching unrelated transcripts.

3. **Grounded Refusal Boundary**:
   - If no chunk exceeds the minimum score threshold (`min_score=0.05`), the retriever returns an empty list `[]`.
   - The system prompt strictly binds the model to refuse:
     > *"I searched Lenny's Podcast transcripts, but this topic is not covered in the archive."*
   - This eliminates pre-trained hallucination on out-of-domain queries.

---

## 5. Security & Sandbox Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│ HOST CLIENT: http://localhost:3000 (Next.js)                           │
│ Holds user session state, local preferences                            │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ <iframe sandbox="allow-scripts" src="/api/artifacts/:id/raw">  │   │
│   │                                                                │   │
│   │ VERTICAL ISOLATION (Browser Engine)                            │   │
│   │ • sandbox="allow-scripts" permits interactive calculator math  │   │
│   │ • Strictly omits allow-same-origin -> origin: "null"           │   │
│   │ • window.parent access throws DOMException SecurityError       │   │
│   │                                                                │   │
│   │ HORIZONTAL CONTAINMENT (HTTP Content-Security-Policy)          │   │
│   │ • default-src 'none'                                           │   │
│   │ • script-src 'unsafe-inline'                                   │   │
│   │ • style-src 'unsafe-inline'                                    │   │
│   │ • connect-src 'none' (blocks fetch, XHR, WebSockets)           │   │
│   │ • img-src data: (blocks external beacon exfiltration)          │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Database Schema & Persistence Model

```mermaid
erDiagram
    SESSIONS ||--o{ MESSAGES : "has many (CASCADE)"
    SESSIONS ||--o{ ARTIFACTS : "has many (CASCADE)"
    MESSAGES ||--o| ARTIFACTS : "originates (SET NULL)"

    SESSIONS {
        string id PK
        string title
        datetime created_at
        datetime updated_at
        json user_metadata
    }

    MESSAGES {
        string id PK
        string session_id FK
        string role
        text content
        json sources
        json model_info
        datetime created_at
    }

    ARTIFACTS {
        string id PK
        string session_id FK
        string message_id FK
        string type
        string title
        text content
        json model_info
        datetime created_at
    }

    ROUTING_LOGS {
        string id PK
        string task
        string provider
        string model
        float latency_ms
        boolean fallback_used
        datetime created_at
    }
```
