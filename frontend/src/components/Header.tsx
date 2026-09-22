"use client";

import { HealthStatus, PublicConfig } from "@/types";
import { Database, Cpu, Cloud, Menu, Radio } from "lucide-react";

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
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur px-4 flex items-center justify-between shrink-0 z-10">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          title="Toggle Sessions"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 via-indigo-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Radio className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
              The Lenny Growth Assistant
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                v{config?.version || "1.0"}
              </span>
            </h1>
            <p className="text-xs text-slate-400 hidden sm:block">
              Grounded in Lenny's Podcast Transcripts
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        {/* System Health Indicators */}
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs">
          <div className="flex items-center gap-1.5 px-1.5 py-0.5" title="Postgres / SQLite Status">
            <Database className="w-3.5 h-3.5 text-slate-400" />
            <span className={`w-2 h-2 rounded-full ${health?.db ? "bg-emerald-400 shadow-sm shadow-emerald-400/50" : "bg-red-400"}`} />
            <span className="text-slate-300 font-mono text-[11px]">DB</span>
          </div>

          <div className="h-3 w-[1px] bg-slate-800" />

          <div className="flex items-center gap-1.5 px-1.5 py-0.5" title="Local Ollama Host Status">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className={`w-2 h-2 rounded-full ${health?.ollama ? "bg-emerald-400 shadow-sm shadow-emerald-400/50" : "bg-amber-400"}`} />
            <span className="text-slate-300 font-mono text-[11px]">Ollama (3B)</span>
          </div>

          <div className="h-3 w-[1px] bg-slate-800" />

          <div className="flex items-center gap-1.5 px-1.5 py-0.5" title="Cloud LLM Status">
            <Cloud className="w-3.5 h-3.5 text-slate-400" />
            <span className={`w-2 h-2 rounded-full ${health?.cloud_llm_configured ? "bg-emerald-400 shadow-sm shadow-emerald-400/50" : "bg-slate-600"}`} />
            <span className="text-slate-300 font-mono text-[11px]">Cloud</span>
          </div>
        </div>

        {/* Model Provider Picker */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-400 hidden xl:inline">Model:</span>
          <select
            value={selectedProvider}
            onChange={(e) => onSelectProvider(e.target.value)}
            className="bg-slate-900 text-slate-200 border border-slate-700 hover:border-slate-600 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition cursor-pointer"
          >
            <option value="auto">Auto (Task Router)</option>
            <option value="ollama">Local: Ollama (llama3.2:3b)</option>
            <option value="gemini" disabled={!config?.providers?.gemini?.configured}>
              Cloud: Gemini 2.0 Flash {!config?.providers?.gemini?.configured ? "(No API Key)" : ""}
            </option>
            <option value="openrouter" disabled={!config?.providers?.openrouter?.configured}>
              Cloud: OpenRouter {!config?.providers?.openrouter?.configured ? "(No API Key)" : ""}
            </option>
          </select>
        </div>
      </div>
    </header>
  );
};
