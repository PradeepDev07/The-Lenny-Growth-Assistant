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
  Sparkles,
  Wrench
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
    <div className="flex-1 flex flex-col h-full glass rounded-2xl md:rounded-3xl overflow-hidden min-w-0">
      {/* Top Controls Bar */}
      <div className="h-14 border-b border-border-subtle px-4 flex items-center justify-between gap-3 shrink-0 bg-white/30 backdrop-blur-sm">
        <div className="flex items-center gap-1.5 p-1 rounded-xl glass-subtle">
          <button
            onClick={() => setActiveTab("preview")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition active:scale-98 ${
              activeTab === "preview"
                ? "bg-white text-text-primary shadow-sm border border-border"
                : "text-text-secondary hover:text-text-primary hover:bg-white/60"
            }`}
          >
            {activeArtifact?.type === "html" ? (
              <Code2 className="w-3.5 h-3.5 text-success" />
            ) : (
              <FileText className="w-3.5 h-3.5 text-accent" />
            )}
            <span>Active Artifact</span>
          </button>

          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition active:scale-98 ${
              activeTab === "history"
                ? "bg-white text-text-primary shadow-sm border border-border"
                : "text-text-secondary hover:text-text-primary hover:bg-white/60"
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-text-secondary" />
            <span>Artifacts ({artifactsList.length})</span>
          </button>
        </div>

        {activeArtifact && activeTab === "preview" && (
          <div className="flex items-center gap-1.5 sm:gap-2">
            {activeArtifact.type === "markdown" && (
              <span className="text-[11px] font-mono text-text-tertiary px-2.5 py-1 rounded-full bg-white/70 border border-border-subtle hidden sm:inline">
                {wordCount} words
              </span>
            )}

            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary glass-subtle hover:bg-white/80 transition active:scale-95"
              title="Copy to clipboard"
              aria-label="Copy to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{copied ? "Copied!" : "Copy"}</span>
            </button>

            <button
              onClick={handleDownload}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-text-secondary hover:text-text-primary glass-subtle hover:bg-white/80 transition active:scale-95"
              title="Download artifact"
              aria-label="Download artifact"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Export</span>
            </button>

            <a
              href={`${API_BASE}/api/artifacts/${activeArtifact.id}/raw`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-accent bg-accent-soft hover:bg-accent-soft/80 border border-accent-border transition active:scale-95"
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
            <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">
              Session Artifacts Archive
            </h3>
            {artifactsList.length === 0 ? (
              <div className="text-center py-16 text-xs text-text-tertiary">
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
                  className={`p-3.5 rounded-2xl glass-elevated text-xs cursor-pointer transition-all duration-160 flex items-center justify-between hover:-translate-y-[1px] ${
                    art.id === activeArtifact?.id
                      ? "border-accent-border bg-accent-soft/30 shadow-sm"
                      : "border-white/80 hover:bg-white/80"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {art.type === "html" ? (
                      <div className="w-8 h-8 rounded-xl bg-success-soft border border-success/20 flex items-center justify-center text-success shadow-sm">
                        <Code2 className="w-4 h-4" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-xl bg-accent-soft border border-accent-border flex items-center justify-center text-accent shadow-sm">
                        <FileText className="w-4 h-4" />
                      </div>
                    )}
                    <div>
                      <div className="font-semibold text-text-primary">{art.title}</div>
                      <div className="text-[11px] text-text-tertiary font-mono">
                        {art.type.toUpperCase()} • {new Date(art.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                  <span className="text-[11px] text-accent font-medium hover:underline">View →</span>
                </div>
              ))
            )}
          </div>
        ) : !activeArtifact ? (
          /* Empty State */
          <div className="h-full flex flex-col items-center justify-center text-center p-6">
            <div className="w-11 h-11 rounded-2xl bg-accent-soft border border-accent-border flex items-center justify-center text-accent mb-3.5 shadow-sm">
              <Sparkles className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-semibold text-text-primary mb-1.5">
              No Active Artifact
            </h3>
            <p className="text-xs text-text-secondary max-w-sm mb-6 leading-relaxed">
              Generate a <strong>Ship 30 for 30 Essay</strong> (~1,250 words) or an{" "}
              <strong>Interactive Calculator</strong> from Lenny's Podcast to preview it here.
            </p>
            <div className="flex flex-col gap-2.5 w-full max-w-xs text-left">
              <div className="p-3.5 rounded-2xl glass-elevated border border-white/80 text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-accent mb-1">
                  <FileText className="w-4 h-4 text-accent" />
                  <span>Ship 30 Essay</span>
                </div>
                <span className="text-[11px] text-text-tertiary leading-relaxed block">
                  Hook, 1-3-1 cadence, narrative, framework breakdown, 3 actionable takeaways.
                </span>
              </div>
              <div className="p-3.5 rounded-2xl glass-elevated border border-white/80 text-xs">
                <div className="flex items-center gap-1.5 font-semibold text-success mb-1">
                  <Wrench className="w-4 h-4 text-success" />
                  <span>Interactive Tool</span>
                </div>
                <span className="text-[11px] text-text-tertiary leading-relaxed block">
                  Sandboxed HTML/JS calculator with reactive math and zero parent leaks.
                </span>
              </div>
            </div>
          </div>
        ) : activeArtifact.type === "html" ? (
          /* Sandboxed HTML Iframe */
          <div className="h-full flex flex-col">
            <div className="px-4 py-2 border-b border-border-subtle bg-white/30 backdrop-blur-sm flex items-center justify-between text-[11px] text-text-tertiary font-mono">
              <span className="flex items-center gap-1.5 text-success font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" /> Sandboxed Iframe (origin: null | CSP: connect-src 'none')
              </span>
              <span className="truncate max-w-[200px]">{activeArtifact.title}</span>
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
          <div className="h-full overflow-y-auto p-6 sm:p-8 text-xs leading-relaxed font-sans">
            <div className="max-w-2xl mx-auto prose prose-sm prose-headings:font-semibold prose-headings:text-text-primary prose-p:text-text-secondary prose-p:leading-relaxed prose-li:text-text-secondary prose-strong:text-text-primary prose-code:text-accent prose-code:bg-accent-soft prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-blockquote:border-l-accent prose-blockquote:text-text-secondary">
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
