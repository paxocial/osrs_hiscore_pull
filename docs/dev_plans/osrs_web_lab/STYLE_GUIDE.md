# 🎨 OSRS Web Lab Style Guide (Dark Blue)
**Audience:** osrs.cortalabs.com web UI (FastAPI + HTMX)  
**Palette Mood:** Deep navy + moonlit highlights, gilded rune accents, low-noise gradients.  
**Type Direction:** Geometric sans for UI, sharp serif accents for headings.

---

## 1) Color System
Use CSS variables under `:root` and `.theme-dark`. Keep contrast ≥ 4.5 for body text.

```css
:root {
  --bg-0: #060b1a; /* night sky */
  --bg-1: #0c1329; /* panels */
  --bg-2: #101a33; /* cards */
  --ink-1: #e8f0ff; /* primary text */
  --ink-2: #c7d3f0; /* secondary */
  --accent-1: #3c7ff0; /* primary call-to-action */
  --accent-2: #5ad1ff; /* hover/active */
  --accent-3: #8dc6ff; /* graph lines */
  --gold-1: #f5d06b; /* highlights / clan badges */
  --danger: #ff6b6b;
  --success: #52d69a;
  --border: rgba(255,255,255,0.06);
  --shadow: 0 18px 48px rgba(0, 12, 50, 0.5);
  --gradient-hero: radial-gradient(120% 120% at 20% 10%, rgba(60,127,240,0.25), transparent),
                   radial-gradient(80% 80% at 80% 0%, rgba(138,199,255,0.18), transparent),
                   #060b1a;
}
```

- Backgrounds: `--bg-0` for page, `--bg-1` nav/footer, `--bg-2` cards/modals.  
- Buttons: primary `--accent-1` with subtle outer glow; secondary ghost buttons use `--ink-2` with border.  
- Charts: lines use `--accent-3`, area fill `rgba(90, 209, 255, 0.18)`, gridlines `rgba(255,255,255,0.06)`.

---

## 2) Typography
- **Headlines:** "Space Grotesk" (600–700).  
- **Body/UI:** "Satoshi" or "Manrope" (400–600).  
- **Numeric/mono:** "DM Mono" for XP, levels, and IDs.  
- Use tight letter-spacing for headings; generous line-height (1.5) for body.  
- Apply small-caps accent for clan tags and contest labels.

---

## 3) Layout & Components
- Grid: 12-column, 80–120px gutters desktop; 6-column mobile fallback. Max width 1360px.  
- Cards: 12–16px radius, `backdrop-filter: blur(6px)`, border `--border`, shadow `--shadow`.  
- Nav: left rail on desktop with icon + label; sticky top-bar on mobile. Include clan switcher + search.  
- Buttons: 44px min height; hover -> lift + glow; focus ring `0 0 0 3px rgba(90,209,255,0.35)`.  
- Tables: zebra with subtle gradient; sticky header; inline filters; compact density toggle.  
- Modals/Drawers: use `--bg-2`; blur backdrop; ensure ESC/overlay close.  
- Forms: floating labels, small helper text, input border glow on focus. Use inline validation + toast feedback.

---

## 4) Motion & States
- Page/section load: 200–300ms fade/slide from 8px below.  
- Hover states: color shift + 2px lift; reduce motion option honors `prefers-reduced-motion`.  
- Skeletons: gradient shimmer using `--bg-1` to `--bg-2` stripe.  
- HTMX swaps: use `hx-target` with `transition: opacity 160ms ease, transform 160ms ease`.

---

## 5) Data & Visualization Patterns
- Sparklines: thin lines in `--accent-3`; peaks annotated with small gold dot for “notable gains.”  
- XP/Level charts: dual-axis allowed; ensure readable legends; constrain to dark grid.  
- Delta chips: green for gains, gold for milestones, red for regressions/HCIM losses.  
- Snapshot timeline: vertical stepping line with timestamp, mode badge, delta summary.  
- Contest dashboards: use segmented progress bars with clan colors (gold accent for leaders).

---

## 6) Three.js Usage (opt-in)
- Use for hero scene and “constellation” skill map; lazy-load module (`type="module"`) only on pages that opt in.  
- Provide fallback static illustration when WebGL unsupported; guard on `if (!WEBGL.isWebGLAvailable())`.  
- Limit draw calls (<150) and post-processing (FXAA only). Keep textures under 1MB total.  
- Theme assets: deep blues with emissive cyan runes; subtle particle drift tied to account activity ticks.

---

## 7) HTMX Patterns
- Use `hx-boost="true"` for nav links to avoid full reloads.  
- Forms: `hx-post` to endpoints, `hx-swap="outerHTML"` for inline error handling.  
- Long-running snapshot triggers: fire POST, then poll `/snapshots/status/{id}` with `hx-trigger="load, every 2s"` until `data-state="ready"`.  
- Flash messages delivered via `hx-trigger="revealed"` and auto-dismiss after 4s.

---

## 8) Iconography & Imagery
- Use lightweight SVG set; avoid heavy icon fonts.  
- Rune-inspired glyphs for skills/clans; keep stroke-weight consistent.  
- Background motifs: faint rune circles or map grids at 5–8% opacity; avoid busy textures.

---

## 9) Accessibility
- Text contrast ≥ 4.5; larger text ≥ 3.0.  
- Focus visible on all interactive elements.  
- Keyboard traps avoided in modals; `aria-live="polite"` for HTMX updates.  
- Provide “Disable 3D” toggle and reduced motion preference.
