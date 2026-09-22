# UI/UX & Interaction Design Specification (design.md)

## 1. Design Philosophy

**The Lenny Growth Assistant** is built for founders, growth leaders, and product managers who need immediate, credible answers without fluff. The interface balances high-density information architecture with calm, focused visual hierarchy.

---

## 2. The Split-Pane Studio Layout

Traditional chat interfaces force users into a single scrolling vertical column where conversational banter, 1,250-word essays, and interactive calculators fight for visual space.

We resolved this with a **Dual-Pane Studio Layout**:

```
┌───────────────────────────────────────┬────────────────────────────────────────┐
│ LEFT PANE (48% width)                 │ RIGHT PANE (52% width)                 │
│ Conversation & Control Center         │ Sandboxed Artifact & Preview Studio    │
├───────────────────────────────────────┼────────────────────────────────────────┤
│ • Health probe pills                  │ • Active Artifact preview              │
│ • Model provider override picker      │ • Formatted Markdown (Ship 30 essays)  │
│ • Real-time streaming chat messages   │ • Sandboxed HTML iframe (calculators)  │
│ • Source attribution cards            │ • Session Artifacts archive tab        │
│ • Quick prompt suggestion chips       │ • Export / Copy / Raw in new window    │
│ • Multi-mode selector (Chat/Essay/App)│ • Word count meter                     │
└───────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 3. Progressive Disclosure in Streaming

To maintain maximum perceived performance:
1. **Immediate Token Delivery**: Tokens are streamed to the chat thread as fast as the model generates them (0ms layout delay).
2. **Post-Stream Citation Cards**: Verified source citation cards are held until stream completion (`{"event": "done"}`) and fade in below the answer. This completely prevents text from jumping while the user is actively reading.
3. **Automatic Artifact Docking**: When generating an essay or calculator, the right pane automatically wakes up and renders the artifact as soon as generation finishes.

---

## 4. Visual Hierarchy & Color Palette

- **Canvas Background**: Deep slate-950 (`#020617` / `#090d16`) providing high-contrast readability without harsh OLED black glare.
- **Card Surfaces**: Slate-900 / Slate-850 (`#0f172a` / `#1e293b`) with 1px subtle borders (`#334155`).
- **Brand & Accent Colors**:
  - Primary Action / Chat: Electric Blue (`#2563eb` / `#3b82f6`)
  - Ship 30 Essays: Deep Indigo (`#4f46e5` / `#6366f1`)
  - Interactive Calculators: Emerald Green (`#059669` / `#10b981`)
  - Warnings / Fallback: Amber (`#d97706` / `#f59e0b`)

---

## 5. Responsive Behavior

- **Desktop (≥ 1024px)**: Full split-pane layout with persistent side-by-side chat and artifact preview.
- **Tablet / Mobile (< 1024px)**: Top/bottom vertical split with collapsible session sidebar drawer.
