"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Session,
  Message,
  Artifact,
  HealthStatus,
  PublicConfig,
  GenerationMode,
  SourceCitation
} from "@/types";
import {
  fetchHealth,
  fetchConfig,
  fetchSessions,
  fetchSession,
  createSession,
  deleteSession,
  fetchSessionArtifacts,
  fetchArtifact,
  streamPipeline
} from "@/lib/api";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { ChatPane } from "@/components/ChatPane";
import { ArtifactPane } from "@/components/ArtifactPane";

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [artifactsList, setArtifactsList] = useState<Artifact[]>([]);
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>("auto");
  const [mode, setMode] = useState<GenerationMode>("chat");

  const [inputPrompt, setInputPrompt] = useState<string>("");
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingText, setStreamingText] = useState<string>("");
  const [streamingSources, setStreamingSources] = useState<SourceCitation[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Initial Load: Health, Config, and Sessions
  useEffect(() => {
    async function init() {
      try {
        const [h, c, s] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchConfig().catch(() => null),
          fetchSessions().catch(() => []),
        ]);
        if (h) setHealth(h);
        if (c) setConfig(c);
        if (s && s.length > 0) {
          setSessions(s);
          loadSessionData(s[0].id);
        } else {
          // Auto create initial session
          const newS = await createSession("Getting Started");
          setSessions([newS]);
          loadSessionData(newS.id);
        }
      } catch (err) {
        console.error("Initialization error:", err);
      }
    }
    init();
  }, []);

  const loadSessionData = async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    try {
      const [detail, arts] = await Promise.all([
        fetchSession(sessionId).catch(() => null),
        fetchSessionArtifacts(sessionId).catch(() => []),
      ]);
      if (detail) {
        setMessages(detail.messages || []);
      }
      setArtifactsList(arts || []);
      if (arts && arts.length > 0) {
        // Select the most recent artifact
        setActiveArtifact(arts[arts.length - 1]);
      } else {
        setActiveArtifact(null);
      }
    } catch (err) {
      console.error("Error loading session:", err);
    }
  };

  const handleNewSession = async () => {
    try {
      const newS = await createSession("New Conversation");
      setSessions((prev) => [newS, ...prev]);
      setCurrentSessionId(newS.id);
      setMessages([]);
      setArtifactsList([]);
      setActiveArtifact(null);
      setStreamingText("");
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation and its associated artifacts?")) return;
    try {
      await deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (currentSessionId === sessionId) {
        if (remaining.length > 0) {
          loadSessionData(remaining[0].id);
        } else {
          handleNewSession();
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleSubmit = async (promptOverride?: string) => {
    const promptToSend = (promptOverride || inputPrompt).trim();
    if (!promptToSend || isStreaming) return;

    let targetSessionId = currentSessionId;
    if (!targetSessionId) {
      const newS = await createSession(promptToSend.slice(0, 40));
      setSessions((prev) => [newS, ...prev]);
      targetSessionId = newS.id;
      setCurrentSessionId(targetSessionId);
    }

    // Add optimistic user message to thread
    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      session_id: targetSessionId,
      role: "user",
      content: promptToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputPrompt("");
    setIsStreaming(true);
    setStreamingText("");
    setStreamingSources([]);

    abortControllerRef.current = new AbortController();
    const providerParam = selectedProvider === "auto" ? null : selectedProvider;

    let endpoint = "/api/chat";
    let payload: Record<string, any> = {
      session_id: targetSessionId,
      message: promptToSend,
      provider_override: providerParam,
    };

    if (mode === "essay") {
      endpoint = "/api/skills/essay";
      payload = {
        topic: promptToSend,
        session_id: targetSessionId,
        provider_override: providerParam,
      };
    } else if (mode === "artifact") {
      endpoint = "/api/skills/artifact";
      payload = {
        topic: promptToSend,
        session_id: targetSessionId,
        provider_override: providerParam,
      };
    }

    let accumulatedTokens = "";

    await streamPipeline(
      endpoint,
      payload,
      {
        onToken: (token: string) => {
          accumulatedTokens += token;
          setStreamingText((prev) => prev + token);
        },
        onDone: async (doneData: any) => {
          setIsStreaming(false);
          const assistantMsg: Message = {
            id: `ast-${Date.now()}`,
            session_id: targetSessionId!,
            role: "assistant",
            content: accumulatedTokens || "Done.",
            sources: doneData.sources || [],
            model_info: doneData.model_info || {},
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);
          setStreamingText("");

          // If an artifact was generated, fetch and display it
          if (doneData.artifact_id) {
            try {
              const art = await fetchArtifact(doneData.artifact_id);
              setActiveArtifact(art);
              setArtifactsList((prev) => [...prev, art]);
            } catch (aErr) {
              console.error("Failed to load generated artifact:", aErr);
            }
          }

          // Refresh session list to reflect message counts & updated timestamps
          fetchSessions().then(setSessions).catch(() => {});
        },
        onError: (err: any) => {
          setIsStreaming(false);
          console.error("Stream error:", err);
          const errorMsg: Message = {
            id: `err-${Date.now()}`,
            session_id: targetSessionId!,
            role: "assistant",
            content: `Generation failed: ${err.message || "Unable to complete request."}`,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, errorMsg]);
        },
      },
      abortControllerRef.current.signal
    );
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden p-2 sm:p-3 md:p-3.5 font-sans text-text-primary">
      {/* Floating Left Sidebar */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        isOpen={sidebarOpen}
        onSelectSession={loadSessionData}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      {/* Main Workspace Canvas */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Floating Top Header */}
        <Header
          health={health}
          config={config}
          selectedProvider={selectedProvider}
          onSelectProvider={setSelectedProvider}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        />

        {/* Spatial Dual Split-Pane Studio */}
        <main className="flex-1 flex flex-col lg:flex-row min-h-0 gap-3 overflow-hidden">
          {/* Left Pane: Conversation & Chat Input */}
          <div className="w-full lg:w-[48%] h-1/2 lg:h-full flex flex-col min-w-0">
            <ChatPane
              messages={messages}
              streamingText={streamingText}
              isStreaming={isStreaming}
              streamingSources={streamingSources}
              mode={mode}
              onSelectMode={setMode}
              inputPrompt={inputPrompt}
              onChangeInput={setInputPrompt}
              onSubmit={handleSubmit}
              onStop={handleStop}
            />
          </div>

          {/* Right Pane: Sandboxed Artifact & Preview Viewer */}
          <div className="w-full lg:w-[52%] h-1/2 lg:h-full flex flex-col min-w-0">
            <ArtifactPane
              activeArtifact={activeArtifact}
              artifactsList={artifactsList}
              onSelectArtifact={setActiveArtifact}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
