# Email & display HTML — WaveAssist house style

Applies whenever a node produces HTML for an email body, a WaveAssist
dashboard `display_output`, or a PDF report. Generated assistants must
look like they came from the same family — consistent palette,
typography, rhythm. WaveAssist's brand is deterministic, engineering-led,
calm. The HTML reflects that. Reference: `WaveContent/send_email.py`.

## Brand palette (light theme — never dark for emails)

| Token | Hex | Use |
|---|---|---|
| `--bg` / `--surface` | `#ffffff` | Page + card background |
| `--ink` | `#0f1116` | Headlines |
| `--ink-2` | `#0f172a` | Body text |
| `--ink-muted` | `#6b7280` | Meta, captions, KV labels |
| `--rule` | `#e5e7eb` | Borders, dividers |
| `--rule-soft` | `#f3f4f6` | KV row separators |
| `--brand` | `#1ED66C` | Accents (left/top borders, badges) |
| `--brand-dark` | `#148F47` | Links |
| `--status-good` | `#15803d` | Healthy / ready |
| `--status-warn` | `#b45309` | Needs-attention |
| `--status-bad` | `#b91c1c` | Critical / blocked |

Status colors live ONLY in small badges and pills. The page stays white;
never paint backgrounds with status hues.

## Typography (system fonts only — no webfonts in email)

```
font-family: Inter, -apple-system, BlinkMacSystemFont,
             "Helvetica Neue", Arial, sans-serif;
```

Mono (for code, commit hashes, IDs):
```
font-family: ui-monospace, "JetBrains Mono", Menlo, Monaco, monospace;
```

Sizes: H1 22/700, H2 18-22/600, H3 14/600, body 14/400 (line-height
1.45), meta 12/400.

## Layout primitives — recurring shapes; do not invent variants

**Header card** (top of every email):
`border:1px solid #e5e7eb; border-top:4px solid #1ED66C; border-radius:12px; padding:14px 16px; background:#fff;`

**Section heading** (H2): green left bar + grey bottom rule, no background.
`border-left:4px solid #1ED66C; border-bottom:1px solid #e5e7eb; padding:10px 0 10px 12px;`

**Item card** (per-PR, per-deal, per-task):
`border:1px solid #e5e7eb; border-left:3px solid #1ED66C; border-radius:12px; padding:12px; margin:10px 0; background:#fff;`

**KV row** (metadata): label 160px wide `#6b7280`, value flex `font-size:12px`, separator `border-top:1px solid #f3f4f6` (none on first row).

**Pill / badge**: `display:inline-block; font-size:11px; padding:2px 8px; border-radius:999px; border:1px solid #e5e7eb; color:#374151;` — for status pills, swap border + color to status hue, keep white background.

**Link**: `color:#148F47; text-decoration:none;`

## Hierarchy rule (non-negotiable)

Lead with the **insight**, then **data**. Reader's eye hits in this order:
1. Header card (what + when)
2. Top-line verdict / health badge (one line)
3. Narrative paragraph (2-3 sentences from a `synthesize`-class node)
4. Per-bucket sections, each with item cards
5. (Optional) Raw appendix at the bottom

If nothing needs highlighting, narrative says so plainly ("Quiet week —
nothing needs you"). Don't pad with empty tables.

## Email-safe HTML

- **Inline CSS only** — no `<style>` blocks for email. Dashboards CAN
  use `<style>`; emails must inline everything.
- **Tables for layout** — Outlook needs `<table cellpadding="0" cellspacing="0">` for width/centering.
- **Max-width 640px wrapper.** Mobile won't reflow without it.
- **No external CSS, no webfonts, no SVG icons, no background-image cards.**
- One emoji per section header at most (or none).

## Don'ts

- **No em-dashes (`—`)** in user-facing copy. Use commas, periods, pipes.
- **No rainbow status colors.** One brand accent + sparing status colors.
- **No "made with ❤️" footers, no marketing copy in transactional emails.**
- **No generic stock phrasing** ("I am pleased to share", "Hope this finds
  you well", "Have a great day") — the persona writes directly.
- **No hardcoded dates in copy** ("Monday morning") unless the user
  pinned them. Use schedule-derived language ("weekly", "this run").

## Reference skeleton — copy this shape, fill the content

```html
<div style="font-family:Inter,-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif;color:#0f172a;max-width:640px;margin:0 auto;padding:18px;background:#ffffff;">

  <!-- Header card -->
  <div style="padding:14px 16px;border:1px solid #e5e7eb;border-top:4px solid #1ED66C;border-radius:12px;background:#ffffff;">
    <h1 style="color:#0f1116;font-size:22px;margin:0 0 6px 0;font-weight:700;">{assistant_name}</h1>
    <div style="color:#6b7280;font-size:12px;">{date} · {scope}</div>
  </div>

  <!-- Top-line verdict -->
  <p style="font-size:14px;line-height:1.45;margin:18px 0 6px 0;">
    <strong>Health:</strong>
    <span style="display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid #e5e7eb;color:#15803d;margin-left:6px;">HEALTHY</span>
  </p>

  <!-- Narrative -->
  <p style="font-size:14px;line-height:1.45;color:#0f172a;">{narrative_from_synthesize_node}</p>

  <!-- Section -->
  <h2 style="color:#0f1116;margin-top:28px;font-size:18px;padding:10px 0 10px 12px;border-left:4px solid #1ED66C;border-bottom:1px solid #e5e7eb;">{section_title}</h2>

  <!-- Item card -->
  <div style="border:1px solid #e5e7eb;border-left:3px solid #1ED66C;border-radius:12px;padding:12px;margin:10px 0;background:#ffffff;">
    <h3 style="margin:0 0 8px 0;font-size:14px;color:#0f1116;">
      <a href="{url}" style="color:#148F47;text-decoration:none;">{title}</a>
    </h3>
    <div style="display:flex;gap:10px;padding:6px 0;">
      <div style="width:160px;color:#6b7280;font-size:12px;">Author</div>
      <div style="flex:1;font-size:12px;">{author}</div>
    </div>
    <div style="display:flex;gap:10px;padding:6px 0;border-top:1px solid #f3f4f6;">
      <div style="width:160px;color:#6b7280;font-size:12px;">Action</div>
      <div style="flex:1;font-size:12px;">{recommended_action}</div>
    </div>
  </div>

  <!-- Footer -->
  <div style="margin-top:26px;text-align:center;color:#6b7280;font-size:12px;">
    Sent by WaveAssist · {assistant_name}
  </div>

</div>
```

Adapt content; don't deviate from palette, typography, or primitive borders/spacing.
