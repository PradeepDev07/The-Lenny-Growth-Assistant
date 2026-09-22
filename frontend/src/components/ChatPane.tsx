"use client";

import React, { useRef, useEffect } from "react";
import { Message, SourceCitation, GenerationMode } from "@/types";
import {
  Send,
  Square,
  Sparkles,
  BookOpen,
  Wrench,
  Bot,
  User as UserIcon,
  ExternalLink,
  Zap,
  CheckCircle2,
  TrendingUp,
  Target,
  Compass
} from "lucide-react";

interface ChatPaneProps {
  messages: Message[];
  streamingText: string;
  isStreaming: boolean;
  streamingSources: SourceCitation[];
  mode: GenerationMode;
  onSelectMode: (m: GenerationMode) => void;
  inputPrompt: string;
  onChangeInput: (val: string) => void;
  onSubmit: (promptOverride?: string) => void;
  onStop: () => void;
}

const QUICK_PROMPTS = [
  {
    icon: TrendingUp,
    label: "Brian Balfour: Growth Loops",
    query: "What are the three main types of growth loops according to Brian Balfour?"
  },
  {
    icon: Target,
    label: "Elena Verna: PLG Activation",
    query: "How does Elena Verna define activation and what are the key benchmark metrics?"
  },
  {
    icon: Compass,
    label: "Shreyas Doshi: LNO Matrix",
    query: "Explain Shreyas Doshi's LNO framework and how a PM should categorize their work."
  },
  {
    icon: Zap,
    label: "Lenny: PMF Signals",
    query: "What are the tell-tale qualitative and quantitative signs of product-market fit according to Lenny?"
  },
];

export const ChatPane: React.FC<ChatPaneProps> = ({
  messages,
  streamingText,
  isStreaming,
  streamingSources,
  mode,
  onSelectMode,
  inputPrompt,
  onChangeInput,
  onSubmit,
  onStop,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full glass rounded-2xl md:rounded-3xl overflow-hidden relative min-w-0">
      {/* Mode Selector Header Bar */}
      <div className="p-3 border-b border-border-subtle flex items-center justify-between gap-2 shrink-0 bg-white/30 backdrop-blur-sm">
        <div className="flex items-center gap-1 p-1 rounded-xl glass-subtle">
          <button
            onClick={() => onSelectMode("chat")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition active:scale-98 ${
              mode === "chat"
                ? "bg-accent text-white shadow-sm shadow-accent/20 font-semibold"
                : "text-text-secondary hover:text-text-primary hover:bg-white/60"
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            <span>RAG Q&A</span>
          </button>

          <button
            onClick={() => onSelectMode("essay")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition active:scale-98 ${
              mode === "essay"
                ? "bg-accent text-white shadow-sm shadow-accent/20 font-semibold"
                : "text-text-secondary hover:text-text-primary hover:bg-white/60"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Ship 30 Essay</span>
          </button>

          <button
            onClick={() => onSelectMode("artifact")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition active:scale-98 ${
              mode === "artifact"
                ? "bg-accent text-white shadow-sm shadow-accent/20 font-semibold"
                : "text-text-secondary hover:text-text-primary hover:bg-white/60"
            }`}
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Interactive Tool</span>
          </button>
        </div>

        <span className="text-[11px] text-text-tertiary hidden xl:inline font-mono">
          {mode === "chat"
            ? "Grounded transcript answers"
            : mode === "essay"
            ? "~1,250 words atomic format"
            : "Reactive HTML/JS calculator"}
        </span>
      </div>

      {/* Message Thread */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-5"
      >
        {messages.length === 0 && !streamingText ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4 py-8">
            <div className="w-11 h-11 rounded-2xl bg-accent-soft border border-accent-border flex items-center justify-center text-accent mb-3.5 shadow-sm">
              <Sparkles className="w-5 h-5" />
            </div>
            <h2 className="text-sm sm:text-base font-semibold text-text-primary mb-1">
              Ask Lenny Growth Assistant
            </h2>
            <p className="text-xs text-text-secondary max-w-md mb-6 leading-relaxed">
              Every answer is verified against transcripts from Brian Balfour, Elena Verna, Shreyas Doshi, and Lenny Rachitsky.
            </p>

            {/* Quick Prompts Grid */}
            <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
              {QUICK_PROMPTS.map((qp, idx) => {
                const IconComponent = qp.icon;
                return (
                  <button
                    key={idx}
                    onClick={() => onSubmit(qp.query)}
                    className="p-3 rounded-xl glass-elevated hover:bg-white/90 border border-white/80 hover:border-accent-border text-xs text-text-secondary transition-all duration-160 hover:-translate-y-[1px] group flex flex-col justify-between"
                  >
                    <span className="font-semibold text-text-primary group-hover:text-accent transition mb-1 flex items-center gap-1.5">
                      <IconComponent className="w-3.5 h-3.5 text-accent" />
                      {qp.label}
                    </span>
                    <span className="text-[11px] text-text-tertiary line-clamp-2">
                      {qp.query}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 text-xs leading-relaxed ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role !== "user" && (
                  <div className="w-7 h-7 rounded-xl bg-accent-soft border border-accent-border flex items-center justify-center text-accent shrink-0 mt-0.5 shadow-sm">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-4 space-y-3 ${
                    msg.role === "user"
                      ? "bg-accent text-white shadow-sm shadow-accent/20 ml-auto"
                      : "glass-elevated border border-white/85 text-text-primary shadow-sm"
                  }`}
                >
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                  {/* Sources Cards */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-2 border-t border-border-subtle space-y-1.5">
                      <div className="text-[10px] uppercase font-mono font-semibold text-text-tertiary flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-success" /> Grounded Transcript Sources:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.sources.map((src, sIdx) => (
                          <a
                            key={sIdx}
                            href={src.url || "#"}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg glass-subtle text-[11px] text-text-secondary hover:text-accent hover:border-accent-border transition"
                          >
                            <span>{src.guest} — {src.source_title}</span>
                            <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Model Telemetry */}
                  {msg.model_info && (
                    <div className="flex items-center gap-2 text-[10px] text-text-tertiary pt-1 font-mono">
                      <span>Model: {msg.model_info.model}</span>
                      <span>•</span>
                      <span>{msg.model_info.latency_ms}ms</span>
                      {msg.model_info.fallback_used && (
                        <span className="text-warning font-semibold">• Fallback Active</span>
                      )}
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="w-7 h-7 rounded-xl glass-elevated border border-white/85 flex items-center justify-center text-accent shrink-0 mt-0.5 shadow-sm">
                    <UserIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {/* Active Streaming Message */}
            {isStreaming && (
              <div className="flex gap-3 text-xs leading-relaxed justify-start">
                <div className="w-7 h-7 rounded-xl bg-accent-soft border border-accent-border flex items-center justify-center text-accent shrink-0 mt-0.5 shadow-sm">
                  <Bot className="w-4 h-4 animate-pulse" />
                </div>
                <div className="max-w-[85%] rounded-2xl p-4 glass-elevated border border-white/85 text-text-primary shadow-sm space-y-3">
                  <div className="whitespace-pre-wrap leading-relaxed">
                    {streamingText || "Searching podcast transcripts..."}
                  </div>

                  {streamingSources.length > 0 && (
                    <div className="pt-2 border-t border-border-subtle space-y-1.5">
                      <div className="text-[10px] uppercase font-mono font-semibold text-text-tertiary flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-success" /> Grounded Transcript Sources:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {streamingSources.map((src, sIdx) => (
                          <span
                            key={sIdx}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg glass-subtle text-[11px] text-text-secondary"
                          >
                            <span>{src.guest} — {src.source_title}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input Box Dock */}
      <div className="p-3.5 border-t border-border-subtle bg-white/40 backdrop-blur-sm shrink-0">
        <div className="relative flex items-end gap-2 glass-input rounded-2xl p-2.5">
          <textarea
            ref={inputRef}
            rows={2}
            value={inputPrompt}
            onChange={(e) => onChangeInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === "chat"
                ? "Ask a question about growth loops, activation, LNO..."
                : mode === "essay"
                ? "Topic for Ship 30 for 30 essay (e.g. 'B2B Growth Loops vs Funnels')..."
                : "Topic for interactive calculator (e.g. 'Elena Verna Activation Rate Calculator')..."
            }
            className="w-full bg-transparent text-text-primary placeholder-text-tertiary text-xs resize-none focus:outline-none px-2 py-1 max-h-32"
          />

          <div className="flex items-center gap-1">
            {isStreaming ? (
              <button
                onClick={onStop}
                className="p-2 rounded-xl bg-error hover:bg-error/90 text-white transition active:scale-95 shadow-sm shadow-error/25"
                title="Stop generation"
                aria-label="Stop generation"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                onClick={() => onSubmit()}
                disabled={!inputPrompt.trim()}
                className="p-2 rounded-xl bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:hover:bg-accent text-white transition active:scale-95 shadow-sm shadow-accent/25"
                title="Send query"
                aria-label="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between text-[11px] text-text-tertiary mt-2 px-1">
          <span>Press Enter to send, Shift+Enter for new line</span>
          <span>Local Ollama fallback enabled</span>
        </div>
      </div>
    </div>
  );
};
