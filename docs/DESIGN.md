# DESIGN.md — Fanthom Brand Kit & UI Rules

> Every screen and component follows this file. If something is not covered here, choose the calmer, simpler option and add the rule here.

---

## 1. Brand idea

**Name:** Fanthom
**Idea:** _depth + clarity._ A fathom is a unit for measuring how deep the water is. Fanthom measures what really happened in a meeting, and every claim points to the moment it was said.
**Tagline:** _Meeting notes that show their receipts._
**Personality:** calm, precise, trustworthy, quietly confident. An executive notebook, not a neon AI dashboard.

**Design principles**
1. **Content over chrome:** the transcript and summary are the product, so UI frames get out of the way.
2. **Every claim is traceable:** citations (timestamp chips) are a first-class visual element, never hidden.
3. **Time is the spine:** timestamps, speaker lanes and the player are always in sync.
4. **Quiet by default, loud only for state:** color is used for speakers, status and the one primary action per screen.

## 2. Logo

- Wordmark: **fanthom** in lowercase, Geist Semibold, letter-spacing −0.02em.
- Mark: three horizontal sonar lines of decreasing width inside a 24×24 rounded square (radius 6), using the `--primary` fill and `--accent` lines. Build it as an inline SVG component `components/brand/Logo.tsx`.
- Minimum size: 20px mark, 80px wordmark. Clear space = height of the mark on every side.
- Never: gradients, drop shadows, stretched, or recolored outside the palette.

## 3. Color

All colors are CSS variables (shadcn convention) defined in `app/globals.css`. **Components use tokens only, never hex.**

### Core palette — light (default)
| Token | Hex | Use |
|---|---|---|
| `--background` | `#FAFAF7` | App background (warm paper) |
| `--surface` | `#FFFFFF` | Cards, panels, player area |
| `--surface-muted` | `#F3F2EE` | Sidebar, hover rows, code blocks |
| `--border` | `#E6E4DE` | Hairline dividers (1px) |
| `--foreground` | `#15181E` | Main text |
| `--muted-foreground` | `#6A6F78` | Secondary text, timestamps labels |
| `--primary` | `#0B2E3F` | "Abyss": primary buttons, logo, active nav |
| `--primary-foreground` | `#FFFFFF` | Text on primary |
| `--accent` | `#0E9F9A` | "Sonar": links, focus ring, citation chips, progress |
| `--accent-soft` | `#E3F5F4` | Citation chip background, selected segment |
| `--highlight` | `#F5A524` | "Marker": current playing segment bar, highlights (F7) |
| `--highlight-soft` | `#FFF4DC` | Highlighted transcript background |

### Status colors
| Token | Hex | Use |
|---|---|---|
| `--success` | `#16A34A` | Ready |
| `--warning` | `#D97706` | Processing (transcribing / summarizing) |
| `--danger` | `#DC2626` | Failed, destructive actions |
| `--info` | `#2563EB` | Neutral info toasts |

### Dark mode (optional, only if time remains)
`--background #0D1117` · `--surface #151B23` · `--surface-muted #1C232D` · `--border #2A323D` · `--foreground #E8EAED` · `--muted-foreground #9AA3AE` · `--primary #E8EAED` (on dark, primary button is light) · `--accent #2CC7C1` · `--highlight #FFB940`

### Speaker colors (8, assigned by `speakers.color_index`)
Used for the speaker dot, the speaker's lane in the timeline and the left border of their transcript segments. Chosen to be distinct and AA-readable as text on white.

| idx | Hex | Name |
|---|---|---|
| 0 | `#2563EB` | Blue |
| 1 | `#DB2777` | Pink |
| 2 | `#059669` | Green |
| 3 | `#C2410C` | Orange |
| 4 | `#7C3AED` | Violet |
| 5 | `#0891B2` | Cyan |
| 6 | `#B91C1C` | Red |
| 7 | `#4B5563` | Slate |

9+ speakers: reuse colors in order and always show the name next to the dot (never rely on color alone).

## 4. Typography

| Role | Font | Notes |
|---|---|---|
| UI + body | **Geist Sans** (`next/font`) | Default for everything |
| Timestamps, durations, IDs | **Geist Mono** | Use `tabular-nums` so times don't jump |

| Style | Size / line-height | Weight | Use |
|---|---|---|---|
| Display | 40 / 48 | 600 | Landing hero only |
| H1 | 28 / 36 | 600 | Page title (meeting title) |
| H2 | 20 / 28 | 600 | Panel titles ("Summary", "Transcript") |
| H3 | 16 / 24 | 600 | Summary section headings |
| Body | 15 / 24 | 400 | Transcript text, summary bullets |
| Small | 13 / 20 | 400 / 500 | Meta, labels, speaker names |
| Mono small | 12 / 16 | 500 | Timestamps, chips |

Letter-spacing: −0.01em for H1–H2. Max reading width for transcript and summary: **72ch**.

## 5. Spacing, radius, elevation

- Spacing scale (4px base): `4, 8, 12, 16, 24, 32, 48, 64`. Panels use 24 inside padding; lists use 12 between rows.
- Radius: `--radius-sm 6px` (chips, inputs) · `--radius 10px` (buttons, cards) · `--radius-lg 14px` (modals, player).
- Borders over shadows. Shadow only for floating layers: `0 8px 24px rgba(15, 24, 30, 0.08)` (popovers, dialogs, toasts).
- Motion: 150ms ease-out for hover/press, 200ms for panels. Smooth-scroll transcript to the active segment. Respect `prefers-reduced-motion` (no auto-scroll animation, instant jumps).

## 6. Layout

**App shell:** left sidebar 240px (`--surface-muted`) with logo, "New meeting" primary button, nav (Meetings, Search), and at the bottom a "Demo workspace" badge. Content area max-width 1280px, 32px side padding.

**Meeting page (desktop ≥ 1024px):**
```
┌──────────────────────────────────────────────────────────────┐
│ ← Meetings   Plan team weekly sync      56:12 · 8 speakers  [Share] │
├───────────────────────────────────┬──────────────────────────┤
│ Player (16:9 video or audio wave) │  Tabs: Transcript | Ask AI │
│ Speaker timeline (lanes)          │  [search in transcript]    │
│ ───────────────────────────────── │  ● Sara  02:14             │
│ Summary  [template ▾]             │  text… (active = marker)   │
│  ▸ Key decisions  [02:14] [11:40] │  ● Ali   02:31             │
│  ▸ Action items  ☐ … [18:05]      │  text…                     │
└───────────────────────────────────┴──────────────────────────┘
          left 60%                           right 40% (sticky)
```
**Tablet (768–1023):** one column. Player, then tabs: Summary | Transcript | Ask AI.
**Mobile (< 768):** same as tablet, sticky mini-player at the top while scrolling.

## 7. Components

| Component | Rules |
|---|---|
| **Button** | Primary = `--primary` fill. Secondary = `--surface` + border. Ghost for toolbars. Height 36 (sm 32). One primary button per view. |
| **Status badge** | Pill, Small text, dot + label: `Processing…` (warning, pulsing dot), `Ready` (success), `Failed` (danger). Processing shows the step: "Transcribing", "Writing summary". |
| **Citation chip** | Mono 12px, `--accent-soft` bg, `--accent` text, radius 6, e.g. `▶ 11:40`. Click = seek player + scroll transcript + flash the segment for 1.2s with `--highlight-soft`. Tooltip shows the speaker and the first 80 chars of that segment. |
| **Transcript segment** | 3px left border in speaker color. Header row: speaker dot + name (Small 500) + timestamp (Mono, muted, clickable). Active (currently playing) segment: `--highlight` left bar + `--highlight-soft` bg. |
| **Speaker timeline** | One 8px-tall lane per speaker, colored blocks where they spoke, name + talk-time % on the left. Playhead = 1px `--foreground` line. Click = seek. |
| **Summary section** | H3 heading, bullets in Body. Each bullet ends with its citation chips. Never show a bullet without at least one chip. |
| **Action item** | Checkbox + text + owner pill (speaker color dot + name) + chip. |
| **Ask AI** | Suggested questions as ghost buttons when empty. Answers stream in. Citation chips render inline as they appear. |
| **Meeting card / row** | Title (16/600), date · duration · speaker avatars (dots, max 4 + "+n"), status badge, 2-line summary preview. |
| **Upload dropzone** | Dashed `--border` 2px, radius 14, icon + "Drop a recording or click to choose" + accepted formats and size limit. Drag-over state: `--accent` border + `--accent-soft` bg. |
| **Toast** | Bottom-right, surface + shadow, icon colored by status, auto-dismiss 4s (errors stay until closed). |

## 8. States (required everywhere)

- **Loading:** skeletons shaped like the final content (rows, chips). Never a full-page spinner after first paint.
- **Empty:** short headline + one sentence + one action. e.g. _"No meetings yet. Upload a recording or open a demo meeting."_
- **Processing:** a progress card with the current step ("Uploading 64%", "Transcribing… usually under 1 min for a 30-min call", "Writing summary…").
- **Error:** what happened + what to do + retry button. e.g. _"We couldn't hear anyone speaking in this file. Check that it has audio and try another file."_ Never show raw stack traces or provider names in user-facing errors.

## 9. Voice & microcopy

- Plain, short, active. "Upload a recording", not "Initiate media ingestion".
- Name what happened and the next step. No blame, no "Oops!".
- Times always as `mm:ss` (or `h:mm:ss` over an hour).
- AI copy is factual and attributed: "Sara agreed to send the deck by Friday ▶ 18:05", not "The team had a productive discussion."

## 10. Accessibility

- WCAG AA contrast for all text (tokens above are chosen for this, so don't lighten them).
- Visible focus ring: 2px `--accent`, offset 2px.
- Speakers are never identified by color alone; the name is always shown.
- Keyboard: `Space` play/pause (when not typing), `←/→` seek 5s, `/` focus transcript search, `Enter` on a chip seeks.
- Player and chips have `aria-label`s, e.g. "Play from 11 minutes 40 seconds".
- Captions: the transcript panel acts as captions, and the active segment is announced with `aria-live="polite"` only when the user turns on "Follow along".

## 11. Tailwind v4 tokens (paste into `app/globals.css`)

```css
@theme inline {
  --color-background: var(--background);
  --color-surface: var(--surface);
  --color-surface-muted: var(--surface-muted);
  --color-border: var(--border);
  --color-foreground: var(--foreground);
  --color-muted-foreground: var(--muted-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-accent: var(--accent);
  --color-accent-soft: var(--accent-soft);
  --color-highlight: var(--highlight);
  --color-highlight-soft: var(--highlight-soft);
  --color-success: var(--success);
  --color-warning: var(--warning);
  --color-danger: var(--danger);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
  --radius-sm: 6px;
  --radius: 10px;
  --radius-lg: 14px;
}

:root {
  --background: #FAFAF7; --surface: #FFFFFF; --surface-muted: #F3F2EE; --border: #E6E4DE;
  --foreground: #15181E; --muted-foreground: #6A6F78;
  --primary: #0B2E3F; --primary-foreground: #FFFFFF;
  --accent: #0E9F9A; --accent-soft: #E3F5F4;
  --highlight: #F5A524; --highlight-soft: #FFF4DC;
  --success: #16A34A; --warning: #D97706; --danger: #DC2626; --info: #2563EB;
  --speaker-0: #2563EB; --speaker-1: #DB2777; --speaker-2: #059669; --speaker-3: #C2410C;
  --speaker-4: #7C3AED; --speaker-5: #0891B2; --speaker-6: #B91C1C; --speaker-7: #4B5563;
}
```
