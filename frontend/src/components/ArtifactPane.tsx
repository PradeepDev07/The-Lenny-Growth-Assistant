"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Artifact } from "@/types";
import { API_BASE } from "@/lib/api";
import {
  FileText,
  Code2,
  Copy,
  Check,
  Download,
  ExternalLink,
  ShieldCheck,
  Layers,
  Sparkles
} from "lucide-react";

interface ArtifactPaneProps {
  activeArtifact: Artifact | null;
  artifactsList: Artifact[];
  onSelectArtifact: (art: Artifact) => void;
}

export const ArtifactPane: React.FC<ArtifactPaneProps> = ({
  activeArtifact,
  artifactsList,
  onSelectArtifact,
}) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"preview" | "history">("preview");

  const handleCopy = () => {
    if (!activeArtifact) return;
    navigator.clipboard.writeText(activeArtifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!activeArtifact) return;
    const blob = new Blob([activeArtifact.content], {
      type: activeArtifact.type === "html" ? "text/html" : "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeArtifact.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${
      activeArtifact.type === "html" ? "html" : "md"
    }`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const wordCount = activeArtifact
    ? activeArtifact.content.trim().split(/\s+/).filter(Boolean).length
    : 0;

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 min-w-0">
      {/* Top Controls Bar */}
      <div className="h-14 border-b border-slate-800/80 px-4 flex items-center justify-between gap-3 shrink-0 bg-slate-900/40">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("preview")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === "preview"
                ? "bg-slate-800 text-white shadow-sm border border-slate-700/60"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {activeArtifact?.type === "html" ? (
              <Code2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <FileText className="w-3.5 h-3.5 text-indigo-400" />
            )}
            <span>Active Artifact</span>
          </button>

          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === "history"
                ? "bg-slate-800 text-white shadow-sm border border-slate-700/60"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span>Artifacts ({artifactsList.length})</span>
          </button>
        </div>

        {activeArtifact && activeTab === "preview" && (
          <div className="flex items-center gap-2">
            {activeArtifact.type === "markdown" && (
              <span className="text-[11px] font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 hidden sm:inline">
                {wordCount} words
              </span>
            )}

            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 transition"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{copied ? "Copied!" : "Copy"}</span>
            </button>

            <button
              onClick={handleDownload}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 transition"
              title="Download artifact"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Export</span>
            </button>

            <a
              href={`${API_BASE}/api/artifacts/${activeArtifact.id}/raw`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 transition"
              title="Open raw preview in new tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Raw</span>
            </a>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === "history" ? (
          <div className="h-full overflow-y-auto p-4 space-y-2">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Session Artifacts Archive
            </h3>
            {artifactsList.length === 0 ? (
              <div className="text-center py-16 text-xs text-slate-400">
                No artifacts generated in this session yet.
              </div>
            ) : (
              artifactsList.map((art) => (
                <div
                  key={art.id}
                  onClick={() => {
                    onSelectArtifact(art);
                    setActiveTab("preview");
                  }}
                  className={`p-3.5 rounded-xl border text-xs cursor-pointer transition flex items-center justify-between ${
                    art.id === activeArtifact?.id
                      ? "bg-slate-800/90 border-blue-500/50 text-white"
                      : "bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-850 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {art.type === "html" ? (
                      <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                        <Code2 className="w-4 h-4" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                        <FileText className="w-4 h-4" />
                      </div>
                    )}
                    <div>
                      <div className="font-semibold text-white">{art.title}</div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {art.type.toUpperCase()} • {new Date(art.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                  <span className="text-[11px] text-blue-400 hover:underline">View →</span>
                </div>
              ))
            )}
          </div>
        ) : !activeArtifact ? (
          /* Empty State */
          <div className="h-full flex flex-col items-center justify-center text-center p-6">
            <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400 mb-4 shadow-inner">
              <Sparkles className="w-6 h-6 text-blue-400" />
            </div>
            <h3 className="text-sm font-semibold text-white mb-1.5">
              No Active Artifact
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mb-6 leading-relaxed">
              Generate a <strong>Ship 30 for 30 Essay</strong> (~1,250 words) or an{" "}
              <strong>Interactive Calculator</strong> from Lenny's Podcast to preview it here.
            </p>
            <div className="flex flex-col gap-2 w-full max-w-xs text-left">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs">
                <span className="font-semibold text-indigo-400 block mb-0.5">📝 Ship 30 Essay</span>
                <span className="text-[11px] text-slate-400">Hook, 1-3-1 cadence, framework breakdown, actionable takeaways.</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs">
                <span className="font-semibold text-emerald-400 block mb-0.5">⚡ Interactive Tool</span>
                <span className="text-[11px] text-slate-400">Sandboxed HTML/JS calculator with reactive math and zero parent leaks.</span>
              </div>
            </div>
          </div>
        ) : activeArtifact.type === "html" ? (
          /* Sandboxed HTML Iframe */
          <div className="h-full flex flex-col">
            <div className="px-4 py-2 bg-slate-950 border-b border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" /> Sandboxed Iframe (origin: null | CSP: connect-src 'none')
              </span>
              <span>{activeArtifact.title}</span>
            </div>
            <div className="flex-1 w-full bg-white relative">
              <iframe
                title={activeArtifact.title}
                sandbox="allow-scripts"
                src={`${API_BASE}/api/artifacts/${activeArtifact.id}/raw`}
                className="w-full h-full border-0 absolute inset-0"
              />
            </div>
          </div>
        ) : (
          /* Rendered Markdown Essay */
          <div className="h-full overflow-y-auto p-6 text-xs text-slate-200 leading-relaxed font-sans scrollbar-thin scrollbar-thumb-slate-800">
            <div className="max-w-2xl mx-auto prose prose-invert prose-xs prose-headings:font-semibold prose-headings:text-white prose-p:text-slate-300 prose-li:text-slate-300 prose-code:text-blue-400 prose-code:bg-slate-900 prose-code:px-1 prose-code:py-0.5 prose-code:rounded">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeArtifact.content}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
