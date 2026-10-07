# DESIGN.md — ASPIRE Design System & UI Specification

> **Target Platform:** ASPIRE Student Success Intelligence Platform
> **Ecosystem:** `apps/web` (Next.js 15 Mentor/Admin Web) & `apps/mobile` (Next.js 15 Student PWA)
> **Design Philosophy:** Sleek, high-density, modern intelligence dashboard (inspired by Linear, Raycast, and Cursor) with rich glassmorphism, crisp contrast, and unmistakable academic risk signaling.

---

## 1. Visual Identity & Atmosphere

### 1.1 Aesthetic Tone
- **Atmosphere:** Deep Space / Sleek Dark Modern with warm ambient lighting and crisp translucent surfaces.
- **Elevation & Layers:** Layered glass cards with subtle 1px border glows (`border-white/[0.08]`), soft backdrop blur (`backdrop-blur-xl`), and dark slate foundations (`bg-[#0B0F17]`, `bg-[#111827]/80`).
- **Interactive Micro-Animations:** Smooth 150ms–200ms ease transitions on hover, active press states (`scale-[0.98]`), subtle glow shadows on action cards, and progress ring animations.

---

## 2. Color System & Design Tokens

### 2.1 Base Canvas & Neutral Surfaces
| Token | Hex / Value | Usage |
|---|---|---|
| `--bg-canvas` | `#070A10` | Global application root background |
| `--bg-surface-1` | `#0E1422` | Primary container cards, sidebars |
| `--bg-surface-2` | `#151E32` | Nested cards, hover states, interactive table rows |
| `--bg-surface-elevated` | `rgba(26, 36, 60, 0.75)` | Modals, dropdowns, floating command palette |
| `--border-subtle` | `rgba(255, 255, 255, 0.08)` | Standard card and section divider borders |
| `--border-highlight` | `rgba(255, 255, 255, 0.18)` | Hovered element borders and active tabs |

### 2.2 Brand & Semantic Accent Colors
| Token | Hex / Value | Semantic Role |
|---|---|---|
| `--primary-accent` | `#6366F1` (Indigo 500) | Primary actions, active navigation, system badges |
| `--primary-glow` | `#818CF8` (Indigo 400) | Ambient card glow, hero gradients |
| `--secondary-accent` | `#06B6D4` (Cyan 500) | AI recommendation highlights, learning tracks |
| `--accent-violet` | `#A855F7` (Purple 500) | Agent supervisor events, analytics indicators |

### 2.3 Status & Urgency Signaling (Strict Semantic Mapping)
Academic risk levels and state badges MUST use exact semantic mappings:

| Status / Risk Band | Accent Color | Background Pill | Tailwind Classes |
|---|---|---|---|
| **CRITICAL / ATTENDANCE_RISK** | `#F43F5E` (Rose 500) | `rgba(244, 63, 94, 0.12)` | `text-rose-400 bg-rose-500/10 border-rose-500/30` |
| **WARNING / WATCH** | `#F59E0B` (Amber 500) | `rgba(245, 158, 11, 0.12)` | `text-amber-400 bg-amber-500/10 border-amber-500/30` |
| **SAFE / HEALTHY** | `#10B981` (Emerald 500) | `rgba(16, 185, 129, 0.12)` | `text-emerald-400 bg-emerald-500/10 border-emerald-500/30` |
| **PENDING APPROVAL** | `#38BDF8` (Sky 400) | `rgba(56, 189, 248, 0.12)` | `text-sky-400 bg-sky-500/10 border-sky-500/30` |
| **OVERDUE (Display Only)** | `#FB7185` (Rose 400) | `rgba(251, 113, 133, 0.15)` | `text-rose-300 bg-rose-600/20 border-rose-500/40 animate-pulse` |

---

## 3. Typography & Hierarchy

### 3.1 Font Families
- **Primary Body & Display:** `Inter`, `Geist`, or `Plus Jakarta Sans`, system-ui, sans-serif
- **Data, Metric & Code:** `JetBrains Mono`, `Geist Mono`, monospace

### 3.2 Scale & Weights
- **Hero / Stat Number:** `text-3xl font-extrabold tracking-tight font-mono` (e.g., `73.3%` attendance)
- **Page Title:** `text-2xl font-bold tracking-tight text-white`
- **Section Heading:** `text-base font-semibold text-slate-200 uppercase tracking-wider`
- **Body Regular:** `text-sm text-slate-300 leading-relaxed`
- **Micro / Metadata:** `text-xs text-slate-400 font-medium`

---

## 4. Component Patterns & Guidelines

### 4.1 Cards & Containers
```html
<!-- Standard ASPIRE Glass Card -->
<div class="rounded-xl border border-white/[0.08] bg-[#0E1422]/80 backdrop-blur-xl p-5 shadow-lg shadow-black/20 hover:border-white/[0.15] transition-all duration-200">
  ...
</div>
```

### 4.2 Buttons & CTAs
- **Primary Action (Approve / Submit):**
  `bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-medium px-4 py-2.5 rounded-lg shadow-lg shadow-indigo-500/25 active:scale-[0.98] transition-all`
- **Secondary / Ghost:**
  `bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/[0.08] px-4 py-2.5 rounded-lg active:scale-[0.98] transition-all`
- **Danger / Escalate Action:**
  `bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 px-4 py-2.5 rounded-lg transition-all`

### 4.3 Academic Metric Badge (Pill)
```html
<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold font-mono border text-rose-400 bg-rose-500/10 border-rose-500/30">
  <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
  CRITICAL RISK (73%)
</span>
```

### 4.4 Student What-If Attendance Calculator Slider
- Clear real-time recalculation indicator (`"Attend next 3 consecutive classes to reach 75.0%"`).
- Target goal marker line at `75.0%` (Mandatory Institutional Threshold).

---

## 5. Web vs. Mobile UI Specifics

### 5.1 Mentor / Admin Web (`apps/web`)
- **Layout:** High-density 3-column or 2-column workspace with a collapsible sidebar.
- **Triage Queue:** Fast keyboard navigation (arrow keys to move between students, `A` to approve plan, `E` to escalate).
- **Evidence Drawer:** Slide-over drawer displaying exact data provenance, import source, timestamp, and audit trail.

### 5.2 Student Mobile PWA (`apps/mobile`)
- **Mobile-First Layout:** Bottom navigation bar (`Overview`, `Attendance`, `Tasks`, `Plan`).
- **One-Tap Actions:** Big touch-friendly acceptance cards for intervention plans.
- **Notification Banner:** High-priority sticky card for impending attendance risks or overdue deadlines.

---

## 6. Rules for AI Screen & UI Generation (Google Stitch / OpenCode)
1. **Never use generic unstyled HTML or basic white pages.** Every screen must look premium and intentional.
2. **Always include real semantic states:** Active, Hover, Focus, Disabled, Loading (Skeleton screens), and Empty states.
3. **Always display evidence/explanations:** Any AI recommendation card must have an `"Evidence & Calculation"` accordion or footnote.
4. **No fake charts or generic placeholders:** Use SVG progress rings, clean CSS bar meters, and crisp typography.
