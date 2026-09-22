import {
  Session,
  SessionDetail,
  Artifact,
  HealthStatus,
  PublicConfig
} from "@/types";


export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function fetchConfig(): Promise<PublicConfig> {
  const res = await fetch(`${API_BASE}/config`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Config fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_BASE}/api/sessions?limit=50`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to list sessions: ${res.status}`);
  return res.json();
}

export async function createSession(title?: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title || "New Conversation" }),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch session ${sessionId}: ${res.status}`);
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete session ${sessionId}: ${res.status}`);
}

export async function fetchSessionArtifacts(sessionId: string): Promise<Artifact[]> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/artifacts`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch session artifacts: ${res.status}`);
  return res.json();
}

export async function fetchArtifact(artifactId: string): Promise<Artifact> {
  const res = await fetch(`${API_BASE}/api/artifacts/${artifactId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch artifact ${artifactId}: ${res.status}`);
  return res.json();
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (donePayload: any) => void;
  onError: (error: any) => void;
}

/**
 * Universal SSE consumer using Fetch API + ReadableStreamDefaultReader.
 * Supports POST requests with JSON payload and real-time token processing.
 */
export async function streamPipeline(
  endpoint: string,
  payload: Record<string, any>,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      const errText = await response.text();
      let parsedErr = { code: `HTTP_${response.status}`, message: errText };
      try {
        const jsonErr = JSON.parse(errText);
        if (jsonErr.error) parsedErr = jsonErr.error;
      } catch {}
      callbacks.onError(parsedErr);
      return;
    }

    if (!response.body) {
      callbacks.onError({ code: "EMPTY_BODY", message: "Response body stream is empty" });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;
        const lines = part.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const rawJson = line.slice(6).trim();
            if (!rawJson) continue;
            try {
              const data = JSON.parse(rawJson);
              if (data.token !== undefined) {
                callbacks.onToken(data.token);
              } else if (data.event === "done") {
                callbacks.onDone(data);
              } else if (data.error) {
                callbacks.onError(data.error);
              }
            } catch (jsonErr) {
              console.warn("Failed to parse SSE JSON chunk:", rawJson, jsonErr);
            }
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name === "AbortError") {
      console.log("Stream generation aborted by user.");
      return;
    }
    callbacks.onError({ code: "STREAM_ERROR", message: err.message || String(err) });
  }
}
