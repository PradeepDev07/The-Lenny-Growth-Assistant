"use client";

import React from "react";
import { HealthStatus, PublicConfig } from "@/types";
import { Database, Cpu, Cloud, Menu, Sparkles, ChevronDown } from "lucide-react";

interface HeaderProps {
  health: HealthStatus | null;
  config: PublicConfig | null;
  selectedProvider: string;
  onSelectProvider: (provider: string) => void;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  config,
  selectedProvider,
  onSelectProvider,
  onToggleSidebar,
}) => {
  return (
    <header className="glass-elevated rounded-2xl px-4 py-2.5 flex items-center justify-between shrink-0 mb-3 transition-all duration-200">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-2 rounded-xl text-text-secondary hover:text-text-primary hover:bg-white/60 transition active:scale-95"
          title="Toggle Sessions"
          aria-label="Toggle Sessions"
        >
          <Menu className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-accent text-white flex items-center justify-center shadow-sm shadow-accent/25 transition transform hover:rotate-3">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xs sm:text-sm font-semibold text-text-primary tracking-tight">
                The Lenny Growth Assistant
              </h1>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-accent-soft text-accent border border-accent-border font-medium">
                v{config?.version || "1.0"}
              </span>
            </div>
            <p className="text-[11px] text-text-tertiary hidden sm:block">
              Grounded in Lenny's Podcast Transcripts
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* System Health Indicators */}
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full glass-subtle text-xs">
          <div className="flex items-center gap-1.5 px-1 py-0.5" title="Postgres / SQLite Status">
            <Database className="w-3.5 h-3.5 text-text-tertiary" />
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                health?.db ? "bg-success shadow-sm shadow-success/40" : "bg-error"
              }`}
            />
            <span className="text-text-secondary font-mono text-[11px]">DB</span>
          </div>

          <div className="h-3 w-[1px] bg-border-subtle" />

          <div className="flex items-center gap-1.5 px-1 py-0.5" title="Local Ollama Host Status">
            <Cpu className="w-3.5 h-3.5 text-text-tertiary" />
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                health?.ollama ? "bg-success shadow-sm shadow-success/40" : "bg-warning"
              }`}
            />
            <span className="text-text-secondary font-mono text-[11px]">Ollama (3B)</span>
          </div>

          <div className="h-3 w-[1px] bg-border-subtle" />

          <div className="flex items-center gap-1.5 px-1 py-0.5" title="Cloud LLM Status">
            <Cloud className="w-3.5 h-3.5 text-text-tertiary" />
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                health?.cloud_llm_configured ? "bg-success shadow-sm shadow-success/40" : "bg-text-tertiary/40"
              }`}
            />
            <span className="text-text-secondary font-mono text-[11px]">Cloud</span>
          </div>
        </div>

        {/* Model Provider Picker */}
        <div className="relative flex items-center">
          <select
            value={selectedProvider}
            onChange={(e) => onSelectProvider(e.target.value)}
            className="appearance-none glass-subtle text-text-primary rounded-xl pl-3 pr-7 py-1.5 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-accent/25 focus:border-accent transition hover:bg-white/80"
          >
            <option value="auto">Auto (Task Router)</option>
            <option value="ollama">Local: Ollama (llama3.2:3b)</option>
            <option value="gemini" disabled={!config?.providers?.gemini?.configured}>
              Cloud: Gemini 2.0 Flash {!config?.providers?.gemini?.configured ? "(No Key)" : ""}
            </option>
            <option value="openrouter" disabled={!config?.providers?.openrouter?.configured}>
              Cloud: OpenRouter (Nemotron) {!config?.providers?.openrouter?.configured ? "(No Key)" : ""}
            </option>
          </select>
          <ChevronDown className="w-3 h-3 text-text-tertiary absolute right-2.5 pointer-events-none" />
        </div>
      </div>
    </header>
  );
};
