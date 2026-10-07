---
name: Chris Owen Setioko, Career Platform
description: A public resume shipped as an operations document, a labelled carton with a packing slip of what was delivered.
colors:
  kraft: "#b48656"
  kraft-deep: "#9c7144"
  stock: "#f7f2e7"
  stock-shade: "#ece3d1"
  ink: "#1f1a15"
  ink-soft: "#5b4a39"
  ink-faint: "#6a5642"
  rule: "#8a6a48"
  stamp: "#c4302b"
  stamp-deep: "#9a2420"
typography:
  display:
    fontFamily: "Sofia Sans Condensed, Arial Narrow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(3rem, 10vw, 6rem)"
    fontWeight: 850
    lineHeight: 0.88
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Sofia Sans Condensed, Arial Narrow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.6rem, 3.6vw, 2.2rem)"
    fontWeight: 850
    lineHeight: 1
    letterSpacing: "0.04em"
  title:
    fontFamily: "Sofia Sans Condensed, Arial Narrow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.35rem, 2.6vw, 1.6rem)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "0.01em"
  lead:
    fontFamily: "Sofia Sans, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(1.15rem, 2.4vw, 1.4rem)"
    fontWeight: 650
    lineHeight: 1.35
  body:
    fontFamily: "Sofia Sans, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Sofia Sans Condensed, Arial Narrow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 750
    lineHeight: 1.2
    letterSpacing: "0.06em"
  stamp:
    fontFamily: "Sofia Sans Condensed, Arial Narrow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 850
    lineHeight: 1
    letterSpacing: "0.08em"
  count:
    fontFamily: "Sofia Sans Condensed, Arial Narrow, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 850
    lineHeight: 1
    letterSpacing: "0"
    fontFeature: "tnum"
rounded:
  tick: "2px"
  slip-head: "3px"
  inset: "4px"
  stamp: "5px"
  slip: "6px"
spacing:
  gap: "clamp(1rem, 2.5vw, 1.5rem)"
  pad: "clamp(1.15rem, 4vw, 2.5rem)"
  entry: "1.35rem"
  list: "0.75rem"
components:
  stamp:
    backgroundColor: "transparent"
    textColor: "{colors.stamp}"
    typography: "{typography.stamp}"
    rounded: "{rounded.stamp}"
    padding: "0.55rem 1.3rem 0.45rem"
    height: "3.6rem"
  stamp-hover:
    backgroundColor: "{colors.stamp}"
    textColor: "{colors.stock}"
  stamp-active:
    backgroundColor: "{colors.stamp-deep}"
    textColor: "{colors.stock}"
  slip:
    backgroundColor: "{colors.stock}"
    textColor: "{colors.ink}"
    rounded: "{rounded.slip}"
    padding: "0 clamp(1.15rem, 4vw, 2.5rem) clamp(1.15rem, 4vw, 2.5rem)"
  slip-head:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.stock}"
    typography: "{typography.headline}"
    rounded: "{rounded.slip-head}"
    padding: "0.8rem clamp(1.15rem, 4vw, 2.5rem) 0.7rem"
  manifest-cell:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "0.85rem 1rem"
    height: "3.25rem"
  manifest-cell-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.stock}"
  entry-lead:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.stock}"
    rounded: "{rounded.inset}"
    padding: "1.25rem 1.35rem 1.35rem"
---

# Design System: Chris Owen Setioko, Career Platform

## Overview

**Creative North Star: "Dispatch Box"**

The career ships as an operations document. Corrugated kraft board owns the whole ground, and everything readable sits on white label stock laid on top of it: a shipping label up front (who, what, how to reach), then packing slips that list what was delivered, line item by line item. Near-black ink does all the structural work with 2px rules, reversed bars and dashed tear lines. One rubber-stamp red is held back for the contact action, so the only coloured mark on the page is the one thing the reader should do.

The density is that of a well-kept manifest: tight condensed caps for labels and headings, quantities set in tabular figures, and generous plain-sans prose capped at 60ch. Hierarchy comes from inversion and weight, not from colour or size jumps. The world rejects the white-card-on-gray resume template with pill chips. Skills are typed text or a checklist, never chips.

This system covers the public profile only (`body.public`). The admin pages keep their older teal-on-gray look on purpose (`:root`, global `h1`/`h2`, `.admin*`). That look is out of scope here and does not belong to this world.

**Key Characteristics:**
- Kraft board ground with a subtle fibre-noise texture, visible as margin around every slip.
- Label-stock slips with 2px ink borders and 6px corners.
- Ink-reversed header bars on every slip, and ink-reversed lead entries for ranking.
- Dashed tear lines in rule-brown between line items.
- A perforated manifest stub with half-round notches along the foot of the shipping label.
- Stamp red only on the contact action.
- One condensed caps face for labels, one humanist sans for prose. Both are self-hosted under the OFL.

## Colors

A single-hue kraft-and-ink program (every neutral sits near hue 66 in OKLCH) with one saturated red held in reserve.

### Primary
- **Stamp Red** (`stamp`): rubber-stamp ink. Used only on the contact action: the stamp links in the shipping label and in the closing Contact slip, their focus outline, and their hover fill. **Stamp Deep** (`stamp-deep`) is its pressed state (`:active` background and border) and nothing else.

### Neutral
- **Kraft Board** (`kraft`): the page ground behind every slip. It also fills the manifest perforations and notches so they read as holes punched through to the board. It matches the browser `theme-color`.
- **Kraft Deep** (`kraft-deep`): the scrollbar track. This is the board in shadow.
- **Label Stock** (`stock`): the surface of every slip, and the text colour on ink-reversed bars.
- **Stock Shade** (`stock-shade`): secondary text inside reversed ink areas (subtitle, dates, description and skills on the lead experience entry).
- **Carton Ink** (`ink`): text, 2px borders, slip-head bars, the reversed lead entry, manifest dividers, focus rings and the selection background.
- **Faded Ink** (`ink-soft`): secondary text on stock, such as entry subtitles, dates and the skills-used line.
- **Pencil Ink** (`ink-faint`): empty-state text only, set in italic.
- **Tear-Line Brown** (`rule`): dashed tear lines between entries, the dashed summary divider, the skills column rule, and resting underlines on project links. It is never used for text.

### Named Rules
**The Single Stamp Rule.** Stamp red marks the contact action and nothing else: no red headings, no red emphasis, no red icons. If a second element wants red, it has to be a way to reach Chris.

**The Kraft Owns the Ground Rule.** The page background is always kraft board. Content never floats on plain white or gray. It sits on label stock laid on the board, with kraft visible around it.

## Typography

**Display Font:** Sofia Sans Condensed (with Arial Narrow, then system sans)
**Body Font:** Sofia Sans (with ui-sans-serif, system-ui)

**Character:** The condensed face is shipping-label lettering: heavy, tall, uppercase, tracked out for small labels and tightened at display size. Its regular-width sibling carries the prose, so the two read as one family speaking in two registers.

### Hierarchy
- **Display** (850, `clamp(3rem, 10vw, 6rem)`, line-height 0.88, uppercase, balanced, max 14ch): the name on the shipping label. One per page.
- **Headline** (850, `clamp(1.6rem, 3.6vw, 2.2rem)`, line-height 1, +0.04em, uppercase): slip titles, set in stock on the ink bar.
- **Title** (800, `clamp(1.35rem, 2.6vw, 1.6rem)`, line-height 1.1, mixed case): entry titles such as job, project and institution.
- **Lead** (Sofia Sans 650, `clamp(1.15rem, 2.4vw, 1.4rem)`, line-height 1.35, max 40ch): the headline under the name. The contact-slip sentence uses a lighter cousin (600, 1.15rem).
- **Body** (Sofia Sans 400, 1.0625rem, line-height 1.6 to 1.65, max 60ch): summary and entry descriptions. Descriptions preserve the line breaks from the database.
- **Label** (750, about 1.05rem, +0.04 to +0.06em, uppercase): manifest cells, entry dates and slip counts (700, 1rem, +0.08em). The skills-used line uses the same face at 700 in mixed case with "/" separators.
- **Stamp** (850, 2rem, +0.08em, uppercase): contact stamp text only.
- **Count** (850, 1.6rem, tabular figures): manifest quantities.

### Named Rules
**The Long-Title Rule.** Entry titles (h3) stay mixed case, never caps. Database titles can run long (for example "PERMIAS SMC (Indonesian Students Organization at Santa Monica College)"), and caps would make them unreadable. Uppercase is for short, controlled labels: the name, slip heads, manifest cells, dates and stamps.

**The Tabular Quantity Rule.** Any count or date is set with `font-variant-numeric: tabular-nums`, so the manifest reads like a ledger.

## Layout

A single centred column (`width: min(100%, 62rem)`) of slips stacked on the board, with `gap` between them. The body padding on kraft is `clamp(0.75rem, 4vw, 3.5rem)` vertically and `clamp(0.75rem, 4vw, 2rem)` horizontally, so the board always shows at the edges.

The shipping label is a two-column grid: identity (name, lead and summary) on the left, and a contact block on the right, separated by a 2px ink rule. The full-width manifest runs below both. Slips use `pad` on the sides and bottom, and their ink head bar bleeds edge to edge through negative margins. Entries are separated by `entry` padding plus a dashed tear line. Skills flow into up to three columns (`columns: 3 9.5rem`) with a dashed column rule.

At 48rem and below, the label stacks (identity, then contact, then manifest), and the contact rule moves from the left edge to the top. Stamps sit in a row. The manifest becomes a 2-column grid with ink dividers, and the final cell spans both columns. Entry headings stack their dates below the title, and skills drop to two columns.

In print, the system collapses to a clean one-colour resume: white ground, no slips, shadows or manifest, hairline separators, and stamps reduced to plain text followed by their URL.

## Elevation & Depth

Depth is physical and shallow: paper laid on cardboard. Each slip carries one stacked shadow, made of an inset top highlight, a 2px opaque lip that reads as the thickness of the stock, and a soft drop below. Nothing else on the page is lifted. Inversion (ink fill) is the main hierarchy device, not elevation.

### Shadow Vocabulary
- **Label stock on board** (`box-shadow: 0 1px 0 rgb(255 240 210 / 40%) inset, 0 2px 0 rgb(40 22 6 / 22%), 0 14px 26px -16px rgb(40 22 6 / 60%)`): every slip (the shipping label and each section). Never on inner elements.
- **Stamp double rim** (`box-shadow: inset 0 0 0 2px stock, inset 0 0 0 3.5px stamp`): draws the inner rim of the rubber stamp. Swapped on hover so the rim shows in stock against the red fill.

### Named Rules
**The Paper-Thickness Rule.** Only whole slips cast shadows, and every slip casts the same shadow. Inner elements show rank by inversion, not by lift.

## Shapes

Gently squared corners throughout: slips at 6px, stamps at 5px, the reversed lead entry at 4px, slip-head bars at 3px on the top corners only, and checklist ticks at 2px. Borders are 2px ink for structure and 2px dashed rule-brown for tear lines. The stamp alone uses a 3px border.

**The Tear-Off Stub Rule.** The contents manifest is a perforated tear-off stub. A repeating row of punched holes (kraft discs ringed in ink, 18px pitch) runs along its top edge. Half-round notches at both ends cut into the label's side borders, filled with kraft so they read as cut-outs. The perforated stub is the system's one corner device. It is not a decoration to repeat on every slip.

Stamps sit at a fixed -2deg rotation, as if hand-pressed. No other element rotates.

## Components

### Contact Stamp (signature, primary action)
A hand-pressed rubber stamp. It is the only red object on the page.
- **Shape:** 5px corners, 3px stamp-red border plus an inset double rim, rotated -2deg, minimum height 3.6rem.
- **Default:** stamp-red text and rim on transparent (stock shows through), condensed 850 caps at 2rem, and a CSS-drawn chevron (a rotated bordered square) after the text.
- **Hover:** fills with stamp red, text turns stock, and the rim inverts.
- **Active (stamp press):** fill and border go to stamp-deep, plus `translateY(1px) scale(0.98)` and the same rotation.
- **Focus:** a 3px outline in stamp red, offset 3px.
- **Motion:** colour changes over 140ms and the transform over 160ms, both on `cubic-bezier(0.16, 1, 0.3, 1)`. Transitions run only under `prefers-reduced-motion: no-preference`. The state change itself still applies when reduced motion is on.

### Slip (card / container)
- **Corner Style:** 6px.
- **Background:** label stock, with ink text.
- **Border:** 2px solid ink.
- **Shadow Strategy:** Label stock on board (see Elevation & Depth).
- **Internal Padding:** `pad` on the sides and bottom. The top is taken by the slip head.

### Slip Head
A full-bleed ink bar across the top of each section slip, with 3px top corners. The slip title (Headline) sits on the left. On the right, a tabular uppercase count reads "N items" (or "1 item"). The Contact slip head has no count.

### Manifest (navigation)
A contents row of jump links along the foot of the shipping label, shaped as the Tear-Off Stub. There are five equal cells divided by 2px ink rules. Each cell holds an uppercase condensed label with a tabular count right-aligned at baseline. The Contact cell has no count. On hover, a cell inverts to ink with stock text. The focus outline is inset (-5px offset) so it stays inside the cell. On narrow screens it becomes a 2-column grid (see Layout).

### Line Item (entry)
A title (Title, mixed case), a faded subtitle (company, with location at weight 500), dates right-aligned in the label style, a description capped at 60ch, and an optional skills-used line typed in condensed text with "/" separators. Entries are divided by 2px dashed tear lines. Project titles that link carry a rule-brown underline that darkens to ink on hover.

### Lead Entry (rank by inversion)
The first experience entry prints reversed: an ink panel with 4px corners, stock title, stock-shade secondary text and its own padding. The tear line after it is removed. This is the system's only ranking device. Print renders it as a normal entry.

### Checklist (skills)
Skills are a contents checklist, not chips. Each item has a 0.95rem ink-bordered square with a CSS-drawn X (two diagonal gradients), with text at weight 600, laid out in columns with dashed column rules.

### Dispatch Sticker (status notice)
The fallback notice sits on stock with a 2px dashed ink border, 6px corners and weight 600 text. It appears only when the page falls back from live data.

### Empty State
Pencil-ink italic body text inside the slip, such as "No projects listed yet." Every section shows one when its data is missing.

## Do's and Don'ts

### Do:
- **Do** keep kraft board as the page ground, and put every block of content on a label-stock slip with a 2px ink border, 6px corners and the label-stock shadow.
- **Do** reserve stamp red for contact links, with stamp-deep only as their pressed state.
- **Do** rank by inversion. The lead experience entry prints reversed in ink, and nothing else is promoted by colour or lift.
- **Do** set h3 entry titles in mixed case. Keep uppercase for short, controlled labels.
- **Do** set every count and date in tabular figures.
- **Do** separate line items with 2px dashed tear lines in rule-brown.
- **Do** draw small marks (chevrons, ticks, perforations) in CSS from ink or kraft, and keep them on-world.
- **Do** keep the stamp press within the reduced-motion guard. The motion is 1px and a 0.98 scale, nothing larger.

### Don't:
- **Don't** use stamp red for headings, emphasis, borders, native control accents or decoration.
- **Don't** render skills or tags as pill chips or coloured badges. Use typed "/"-separated text or the checklist.
- **Don't** set long database titles in caps.
- **Don't** put content on plain white or gray, or bring the admin teal palette into the public page.
- **Don't** add lift or shadows to inner elements. Only whole slips cast the label-stock shadow.
- **Don't** repeat the perforated stub and notches on every slip. The tear-off stub belongs to the shipping label's manifest.
