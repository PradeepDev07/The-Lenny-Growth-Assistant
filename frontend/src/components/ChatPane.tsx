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
  CheckCircle2
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
  { label: "Brian Balfour: Growth Loops", query: "What are the three main types of growth loops according to Brian Balfour?" },
  { label: "Elena Verna: PLG Activation", query: "How does Elena Verna define activation and what are the key benchmark metrics?" },
  { label: "Shreyas Doshi: LNO Matrix", query: "Explain Shreyas Doshi's LNO framework and how a PM should categorize their work." },
  { label: "Lenny: PMF Signals", query: "What are the tell-tale qualitative and quantitative signs of product-market fit according to Lenny?" },
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
    <div className="flex-1 flex flex-col h-full bg-slate-900/60 border-r border-slate-800/80 relative min-w-0">
      {/* Mode Selector Header Bar */}
      <div className="p-3 border-b border-slate-800/80 bg-slate-950/40 flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-xl">
          <button
            onClick={() => onSelectMode("chat")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              mode === "chat"
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Bot className="w-3.5 h-3.5" />
            <span>RAG Q&A</span>
          </button>

          <button
            onClick={() => onSelectMode("essay")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              mode === "essay"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Ship 30 Essay</span>
          </button>

          <button
            onClick={() => onSelectMode("artifact")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              mode === "artifact"
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Interactive Tool</span>
          </button>
        </div>

        <span className="text-[11px] text-slate-400 hidden xl:inline font-mono">
          {mode === "chat" ? "Grounded transcript answers" : mode === "essay" ? "~1,250 words atomic format" : "Reactive HTML/JS calculator"}
        </span>
      </div>

      {/* Message Thread */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-slate-800"
      >
        {messages.length === 0 && !streamingText ? (
          <div className="h-full flex flex-col items-center justify-center text-center px-4 py-8">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-4 shadow-inner">
              <Sparkles className="w-6 h-6" />
            </div>
            <h2 className="text-base font-semibold text-white mb-1">
              Ask Lenny Growth Assistant
            </h2>
            <p className="text-xs text-slate-400 max-w-md mb-6 leading-relaxed">
              Every answer is verified against transcripts from Brian Balfour, Elena Verna, Shreyas Doshi, and Lenny Rachitsky.
            </p>

            {/* Quick Prompts Grid */}
            <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
              {QUICK_PROMPTS.map((qp, idx) => (
                <button
                  key={idx}
                  onClick={() => onSubmit(qp.query)}
                  className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-blue-500/40 hover:bg-slate-850 text-xs text-slate-300 transition group flex flex-col justify-between"
                >
                  <span className="font-semibold text-white group-hover:text-blue-400 transition mb-1 flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-blue-400" />
                    {qp.label}
                  </span>
                  <span className="text-[11px] text-slate-400 line-clamp-2">
                    {qp.query}
                  </span>
                </button>
              ))}
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
                  <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-2xl p-4 space-y-3 ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white ml-auto"
                      : "bg-slate-800/80 border border-slate-700/60 text-slate-100 shadow-sm"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>

                  {/* Sources Cards */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-2 border-t border-slate-700/60 space-y-1.5">
                      <div className="text-[10px] uppercase font-mono font-semibold text-slate-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Grounded Transcript Sources:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.sources.map((src, sIdx) => (
                          <a
                            key={sIdx}
                            href={src.url || "#"}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-900 border border-slate-700 text-[11px] text-blue-400 hover:text-blue-300 hover:border-blue-500/50 transition"
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
                    <div className="flex items-center gap-2 text-[10px] text-slate-400 pt-1 font-mono">
                      <span>Model: {msg.model_info.model}</span>
                      <span>•</span>
                      <span>{msg.model_info.latency_ms}ms</span>
                      {msg.model_info.fallback_used && (
                        <span className="text-amber-400 font-semibold">• Fallback Active</span>
                      )}
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
                    <UserIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {/* Active Streaming Message */}
            {isStreaming && (
              <div className="flex gap-3 text-xs leading-relaxed justify-start animate-fade-in">
                <div className="w-7 h-7 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
                  <Bot className="w-4 h-4 animate-pulse" />
                </div>
                <div className="max-w-[85%] rounded-2xl p-4 bg-slate-800/80 border border-slate-700/60 text-slate-100 shadow-sm space-y-3">
                  <div className="whitespace-pre-wrap">{streamingText || "Searching podcast transcripts..."}</div>

                  {streamingSources.length > 0 && (
                    <div className="pt-2 border-t border-slate-700/60 space-y-1.5">
                      <div className="text-[10px] uppercase font-mono font-semibold text-slate-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Grounded Transcript Sources:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {streamingSources.map((src, sIdx) => (
                          <span
                            key={sIdx}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-900 border border-slate-700 text-[11px] text-blue-400"
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

      {/* Input Box */}
      <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/80 shrink-0">
        <div className="relative flex items-end gap-2 bg-slate-900 border border-slate-700 focus-within:border-blue-500 rounded-2xl p-2 transition shadow-inner">
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
            className="w-full bg-transparent text-slate-100 placeholder-slate-400 text-xs resize-none focus:outline-none px-2 py-1 max-h-32"
          />

          <div className="flex items-center gap-1">
            {isStreaming ? (
              <button
                onClick={onStop}
                className="p-2 rounded-xl bg-red-600 hover:bg-red-500 text-white transition active:scale-95 shadow-md shadow-red-600/20"
                title="Stop generation"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                onClick={() => onSubmit()}
                disabled={!inputPrompt.trim()}
                className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-400 text-white transition active:scale-95 shadow-md shadow-blue-600/20 disabled:shadow-none"
                title="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 px-1">
          <span>Press Enter to send, Shift+Enter for new line</span>
          <span>Offline Fallback to local Ollama enabled</span>
        </div>
      </div>
    </div>
  );
};
