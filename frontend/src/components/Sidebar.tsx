"use client";

import React from "react";
import { Session } from "@/types";
import { Plus, MessageSquare, Trash2, X, Clock, Compass } from "lucide-react";

interface SidebarProps {
  sessions: Session[];
  currentSessionId: string | null;
  isOpen: boolean;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string, e: React.MouseEvent) => void;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  isOpen,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onCloseMobile,
}) => {
  return (
    <>
      {/* Mobile Glass Backdrop */}
      {isOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/15 backdrop-blur-sm z-30 md:hidden transition-opacity"
        />
      )}

      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-40
          w-72 glass-elevated rounded-2xl md:mr-3
          flex flex-col shrink-0 transition-transform duration-200 ease-in-out
          ${isOpen ? "translate-x-0 m-3 shadow-glass-floating" : "-translate-x-full md:translate-x-0"}
        `}
      >
        {/* New Session Button */}
        <div className="p-3 border-b border-border-subtle flex items-center justify-between gap-2">
          <button
            onClick={onNewSession}
            className="flex-1 flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-white text-xs font-semibold py-2 px-3.5 rounded-xl shadow-sm shadow-accent/25 transition active:scale-[0.98]"
          >
            <Plus className="w-3.5 h-3.5" />
            New Conversation
          </button>

          <button
            onClick={onCloseMobile}
            className="md:hidden p-2 text-text-tertiary hover:text-text-primary rounded-xl hover:bg-white/60 transition"
            aria-label="Close Sidebar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="px-2.5 py-1.5 text-[11px] font-semibold text-text-tertiary uppercase tracking-wider flex items-center justify-between">
            <span>Conversations</span>
            <span className="font-mono text-[10px] text-text-tertiary">{sessions.length}</span>
          </div>

          {sessions.length === 0 ? (
            <div className="text-center py-12 px-4 text-text-tertiary text-xs">
              <Compass className="w-6 h-6 mx-auto mb-2 text-text-tertiary/60" />
              No conversations yet. Start a new session above!
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === currentSessionId;
              return (
                <div
                  key={session.id}
                  onClick={() => onSelectSession(session.id)}
                  className={`
                    group relative flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs transition cursor-pointer
                    ${
                      isActive
                        ? "bg-accent-soft text-text-primary font-medium border border-accent-border shadow-sm"
                        : "text-text-secondary hover:bg-white/60 hover:text-text-primary border border-transparent"
                    }
                  `}
                >
                  {/* Orange active indicator bar */}
                  {isActive && (
                    <span className="absolute left-1 top-2.5 bottom-2.5 w-1 rounded-full bg-accent" />
                  )}

                  <div className="flex items-center gap-2.5 min-w-0 flex-1 pl-1">
                    <MessageSquare
                      className={`w-3.5 h-3.5 shrink-0 transition-colors ${
                        isActive ? "text-accent" : "text-text-tertiary group-hover:text-text-secondary"
                      }`}
                    />
                    <span className="truncate block">{session.title}</span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] text-text-tertiary font-mono px-1.5 py-0.5 rounded-full bg-white/70 border border-border-subtle">
                      {session.message_count}
                    </span>

                    <button
                      onClick={(e) => onDeleteSession(session.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-text-tertiary hover:text-error hover:bg-error-soft rounded-lg transition"
                      title="Delete conversation"
                      aria-label="Delete conversation"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-border-subtle text-[11px] text-text-tertiary flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-text-tertiary/70" /> Auto-persisted
          </span>
          <span className="font-mono text-[10px] text-text-tertiary">Lenny RAG v1.0</span>
        </div>
      </aside>
    </>
  );
};
