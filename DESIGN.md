# DESIGN.md — ASPIRE Design System & UI Specification

> **Platform:** ASPIRE Student Success Intelligence Platform
> **Ecosystem Scope:** `apps/web` (Mother Application & Web Clients) & `apps/mobile` (Student Web/PWA)
> **Design Reference:** Inspired by the design system thinking and interaction quality of **Linear** (via `awesome-design-md`), adapted with complete fidelity into an original **ASPIRE Academic Intelligence** visual identity.

---

## 1. Visual Theme & Atmosphere

### 1.1 Aesthetic Tone: Restrained Technical Precision
- **Canvas Foundation:** Deep void charcoal-black with a faint slate undertone (`#030712` / `#080C14`), establishing a quiet, high-contrast, professional workspace.
- **Surface Elevation Ladder:** A disciplined 4-tier charcoal surface hierarchy with hairline borders (`border-white/[0.07]`), creating subtle depth without gratuitous gradients or heavy shadows.
- **Accent Discipline:** Single primary chromatic brand accent — **Refined Academic Indigo** (`#6366F1` / `#4F46E5`), used strictly for focal interactive actions and active navigation states. Never applied decoratively as background wash.
- **Information Density:** High signal-to-noise ratio. Compact metadata, crisp numerical data, deliberate whitespace, and progressive disclosure over visual clutter.

---

## 2. Color System & Semantic Tokens

### 2.1 Surfaces & Neutrals
| Token | Hex / Value | Semantic Role |
|---|---|---|
| `--color-canvas` | `#030712` | Deepest root canvas |
| `--color-surface-1` | `#0B0F19` | Primary layout cards, sidebars, navigation panels |
| `--color-surface-2` | `#111827` | Elevated cards, list rows, active containers |
| `--color-surface-3` | `#1F2937` | Hover states, active table rows, popover panels |
| `--color-surface-overlay` | `rgba(11, 15, 25, 0.85)` | Drawers, command palettes, modal backdrops (`backdrop-blur-md`) |
| `--color-hairline` | `rgba(255, 255, 255, 0.08)` | Standard card borders and dividers |
| `--color-hairline-strong` | `rgba(255, 255, 255, 0.16)` | Focused inputs, hovered cards, active tab indicators |

### 2.2 Text / Ink Hierarchy
| Token | Hex / Value | Usage |
|---|---|---|
| `--color-ink` | `#F9FAFB` | Primary headers, key metrics, active titles |
| `--color-ink-muted` | `#D1D5DB` | Body copy, table values, section labels |
| `--color-ink-subtle` | `#9CA3AF` | Supporting metadata, timestamps, roll numbers |
| `--color-ink-tertiary` | `#6B7280` | Placeholder text, disabled labels, table column headers |

### 2.3 Semantic Truth & Academic Status Signaling
Academic UI must communicate truth without ambiguity:

| Semantic State | Accent Color | Pill Background | Tailwind Classes | Meaning / Truth Source |
|---|---|---|---|---|
| **CRITICAL RISK** | `#F43F5E` (Rose 500) | `rgba(244, 63, 94, 0.10)` | `text-rose-400 bg-rose-500/10 border-rose-500/25` | Attendance < 75%, urgent academic danger |
| **WARNING / WATCH** | `#F59E0B` (Amber 500) | `rgba(245, 158, 11, 0.10)` | `text-amber-400 bg-amber-500/10 border-amber-500/25` | Attendance 75%–80%, declining performance |
| **SAFE / HEALTHY** | `#10B981` (Emerald 500) | `rgba(16, 185, 129, 0.10)` | `text-emerald-400 bg-emerald-500/10 border-emerald-500/25` | In good standing (Attendance > 80%) |
| **PENDING APPROVAL** | `#0284C7` (Sky 600) | `rgba(2, 132, 199, 0.10)` | `text-sky-400 bg-sky-500/10 border-sky-500/25` | Case/Plan waiting for Student or Mentor sign-off |
| **PROPOSED (AI)** | `#8B5CF6` (Violet 500) | `rgba(139, 92, 246, 0.10)` | `text-violet-400 bg-violet-500/10 border-violet-500/25` | AI-generated recommendation (unverified proposal) |
| **OVERDUE** | `#E11D48` (Rose 600) | `rgba(225, 29, 72, 0.15)` | `text-rose-300 bg-rose-600/20 border-rose-500/35 animate-pulse` | Derived display state (deadline passed) |

---

## 3. Typography & Hierarchy

### 3.1 Font Stack
- **Interface & Display:** `Inter`, `Geist Sans`, or `SF Pro Display`, `-apple-system`, sans-serif
- **Data, Roll Numbers & Formulas:** `JetBrains Mono`, `Geist Mono`, monospace

### 3.2 Typographic Hierarchy
| Level | Font Size | Weight | Line Height | Tracking | Usage |
|---|---|---|---|---|---|
| **Display / Hero Stat** | `36px–48px` | `600` | `1.1` | `-1.2px` | Large attendance stats (e.g. `73.3%`), metric numbers |
| **Page Title** | `24px` | `600` | `1.2` | `-0.5px` | Screen titles in Mother Application & Web |
| **Card Title / Section** | `16px` | `600` | `1.3` | `-0.2px` | Card headers, table section titles |
| **Body (Default)** | `14px` | `400` | `1.5` | `0px` | Standard interface copy, table cell content |
| **Body Small / Meta** | `12px` | `400 / 500` | `1.4` | `0px` | Badges, timestamps, secondary identifiers |
| **Mono Metrics** | `13px` | `500` | `1.4` | `0px` | Student Roll Numbers (`BCREC-CS-2026-042`), case IDs |

---

## 4. Component Patterns & Guidelines

### 4.1 Buttons & Interactive Controls
- **Primary CTA:** Compact solid button in brand indigo.
  `px-3.5 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition-colors duration-150 active:scale-[0.98]`
- **Secondary Action:** Surface-1 neutral with hairline border.
  `px-3.5 py-1.5 text-xs font-medium bg-[#0B0F19] hover:bg-[#111827] text-gray-200 border border-white/[0.08] rounded-md transition-colors`
- **Ghost / Icon Button:**
  `p-1.5 text-gray-400 hover:text-white hover:bg-white/[0.06] rounded-md transition-colors`

### 4.2 Cards & Surfaces
- **Base Panel:** Hairline border, `#0B0F19` background, rounded-lg (`8px`).
- **Interactive Row:** Hover transitions smoothly to `--color-surface-3` with crisp cursor state.
- **Evidence Drawer / Inspector Panel:** Slide-over from right edge with `#0B0F19` background and subtle inner border divider.

### 4.3 Semantic UI Truth Badging
Every metric and status must display its **Truth Level**:
1. **VERIFIED:** Solid neutral pill (`VERIFIED INSTITUTIONAL RECORD`).
2. **DERIVED:** Calculated by engine (`DERIVED ATTENDANCE: 73.3%`).
3. **PROPOSED:** Clearly labelled as AI draft (`PROPOSED RECOVERY SCHEDULE`).

---

## 5. Mother Application UX & Layout Architecture

### 5.1 Command Center Layout (`apps/web/`)
- **Navigation:** Left sidebar (width `240px` or collapsed icon rail `64px`) with structured domain grouping:
  - *Academic Operations:* Students, Faculty, Courses, Batches, Ingestion.
  - *Intelligence & Cases:* Triage Queue, Active Interventions, Escalations.
  - *Governance & Config:* Institution Rules, Agent Policies, Audit Log, System State.
- **List / Detail Split Layout:** Triage queue on left, side-by-side evidence inspector on right for instant review without page jumps.
- **Progressive Disclosure:** Compact summary in list rows $\rightarrow$ click opens detailed trace drawer $\rightarrow$ actionable approval controls.

---

## 6. Do's and Don'ts

### ✅ DO:
- Keep borders thin (`1px` hairline `border-white/[0.08]`).
- Use monospace for roll numbers, case IDs, and numerical percentages.
- Group related metadata into dense, readable key-value strips.
- Provide keyboard shortcuts for fast operational triage (e.g. `J`/`K` navigation, `A` approve).
- Always show the *evidence* behind an urgency badge or risk alert.

### ❌ DO NOT:
- Do NOT use colorful rainbow gradients or neon glowing borders.
- Do NOT create giant empty dashboard cards with single oversized numbers.
- Do NOT use generic purple AI decorations or sparkling star graphics.
- Do NOT make full-screen spreadsheet dumps without visual hierarchy.
- Do NOT treat `PENDING` states as failures or `0%`.
