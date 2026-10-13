---
name: Chris Owen Setioko, Career Platform
description: A classic resume typeset to book standard on screen; the page itself is the document.
colors:
  paper: "#ffffff"
  ink: "#16202b"
  slate: "#4a5563"
  hairline: "#d9dde3"
  separator: "#8a93a0"
  navy: "#1f3a68"
  navy-deep: "#152a4d"
  navy-wash: "#eef2f8"
  navy-line: "#c9d3e3"
typography:
  display:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "clamp(2.5rem, 6.5vw, 3.75rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.3rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "0"
  title:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "1.2rem"
    fontWeight: 600
    lineHeight: 1.3
  lead:
    fontFamily: "Source Serif 4, Georgia, Times New Roman, serif"
    fontSize: "clamp(1.125rem, 2vw, 1.25rem)"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "\"onum\" 1, \"pnum\" 1"
  subhead:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1
  meta:
    fontFamily: "Source Sans 3, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
rounded:
  focus: "2px"
  sm: "4px"
spacing:
  rail: "11rem"
  column-gap: "clamp(1.5rem, 4vw, 3rem)"
  section: "clamp(2rem, 4.5vw, 3rem)"
  entry: "2rem"
  measure-lead: "62ch"
  measure-body: "65ch"
  page-max: "60rem"
components:
  button-primary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1.05rem"
    height: "2.75rem"
  button-primary-hover:
    backgroundColor: "{colors.navy-deep}"
    textColor: "{colors.paper}"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.navy}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 1.05rem"
    height: "2.75rem"
  button-outline-hover:
    backgroundColor: "{colors.navy-wash}"
    textColor: "{colors.navy}"
  nav-link:
    textColor: "{colors.slate}"
    typography: "{typography.label}"
    padding: "0.35rem 0"
  nav-link-hover:
    textColor: "{colors.ink}"
  notice:
    backgroundColor: "{colors.navy-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "0.8rem 1rem"
---

# Design System: Chris Owen Setioko, Career Platform

## Overview

**Creative North Star: "The Typeset Resume"**

The public page is a classic resume set to book standard on screen. There is no theme, no prop and no card: the white page is the document, and everything on it is type, hairline rules and one restrained navy. Hierarchy comes from a serif/sans pairing and from a hanging-heading grid in which section names sit in a left margin rail and line items run down a steady main column.

Density is that of a well-made printed CV: generous section spacing, measured line lengths (62ch lead, 65ch body), dated entries that align on a baseline with their titles. Color does almost no work; the single accent is reserved for things a reader can act on. The same structure carries to paper through a dedicated print sheet.

This world replaces the earlier "Dispatch Box" carton theme. It rejects both the costume resume and the white-card-on-gray template with pill chips.

Scope: this system governs the public profile (everything under the public page scope). The admin pages deliberately keep their older teal-on-gray look (the root defaults, global h1/h2, and the admin rules) and are out of scope; do not migrate them to this system or this system to them without an explicit decision.

**Key Characteristics:**
- Pure white ground, near-black ink, slate secondary, pale hairline rules.
- One Oxford navy, reserved for links, the contact actions, focus and selection.
- Source Serif 4 (optical sizes) for name, section heads, entry titles and lead prose; Source Sans 3 for body, meta and dates.
- Hanging section heads in an 11rem margin rail, sticky while their section scrolls.
- Flat: no shadows, no cards; structure from rules and whitespace.
- A print sheet that renders the same resume on paper.

## Colors

A near-monochrome ink-on-white palette with a single cool navy accent used sparingly.

### Primary
- **Oxford Navy** (navy): links, the primary contact button fill, outline-button borders and text, the focus ring, text selection, and form accent color. It is the only chromatic color on the page.
- **Deep Oxford** (navy-deep): hover state of the primary contact button (fill and border).
- **Navy Wash** (navy-wash): hover fill of outlined contact buttons and the fallback notice background.
- **Navy Line** (navy-line): the resting underline color of linked entry titles and the fallback notice border.

### Neutral
- **Paper White** (paper): the page ground and the text color on navy fills.
- **Ink** (ink): name, section heads, entry titles, subtitles and body text.
- **Slate** (slate): headline under the name, locations, dates, skills-used runs, jump-nav links at rest, empty states and the footer.
- **Hairline** (hairline): the 1px rules above every section and the footer.
- **Separator Gray** (separator): the middle-dot separators between items in a skills-used run.

### Named Rules
**The One Navy Rule.** Navy marks only what can be acted on (links, contact actions, focus, selection). Never use it for headings, decoration or backgrounds beyond the pale wash.

**The Paper Ground Rule.** The public page ground is pure white; there is no tinted page, no card surface and no gray backdrop.

## Typography

**Display Font:** Source Serif 4, variable with optical sizes (with Georgia, Times New Roman, serif)
**Body Font:** Source Sans 3, variable roman and italic (with ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif)

Both families are self-hosted woff2 under the SIL Open Font License (OFL text shipped with the fonts); the serif and sans roman files are preloaded.

**Character:** A book serif with optical sizing gives the name and heads a typeset, editorial authority; a humanist sans keeps prose, meta and dates crisp and quiet beside it.

### Hierarchy
- **Display** (serif 600, clamp(2.5rem, 6.5vw, 3.75rem), line-height 1.05, -0.015em, balanced wrap): the name only, sentence case.
- **Subhead** (sans 500, 1.25rem, 1.4; 1.125rem under 48rem; slate, 44ch): the headline beneath the name.
- **Lead** (serif 400, clamp(1.125rem, 2vw, 1.25rem), 1.6, oldstyle proportional figures, 62ch): the summary paragraph. The contact close uses the same serif at 1.125rem, 52ch.
- **Headline** (serif 600, 1.3rem, 1.25): hanging section heads in the rail. Under 48rem they become 1.625rem, line-height 1.15, stacked above content.
- **Title** (serif 600, 1.2rem, 1.3, balanced wrap): entry titles (role, project, institution).
- **Body** (sans 400, 1.0625rem, 1.6, max 65ch): descriptions; line breaks in the source text are preserved. Entry subtitles use sans 600 at body size, line-height 1.45.
- **Label** (sans 600, 0.9375rem for jump nav; 1rem in contact buttons): navigation and button text.
- **Meta** (sans 400, 0.9375rem, tabular lining figures, slate): dates and skills-used runs. The footer is 0.875rem slate.

### Named Rules
**The Serif Is Structure Rule.** Serif carries the document's skeleton (name, section heads, entry titles, lead prose); sans carries everything read at speed. Do not swap roles.

**The Tabular Dates Rule.** Date ranges always set in tabular lining figures and never wrap, so they align down the column.

## Layout

The page is a single centered column, max 60rem, padded clamp(1.75rem, 6vw, 5rem) top, clamp(1rem, 5vw, 3rem) sides, clamp(2rem, 5vw, 4rem) bottom.

The header is a two-column grid: identity (name and headline) on the left, contact actions aligned right; the summary and the jump nav span below. The jump nav is a wrapping row of links (gap 0.25rem by 1.75rem).

Every section is a two-column grid: an 11rem rail holding the section head, and the content column, separated by clamp(1.5rem, 4vw, 3rem). Sections have clamp(2rem, 4.5vw, 3rem) vertical padding and a 1px hairline rule on top. Entries within a section are spaced 2rem apart. An entry heading puts the title block on the left and the date range on the right, aligned on baseline.

Skills set as a plain multi-column list (3 columns, min 11rem, 2rem gap), not chips.

**Narrow screens (max-width 48rem):** the header stacks (identity, contact, summary, nav) with contact actions left-aligned; sections collapse to one column; section heads become static and larger (1.625rem) with 1.25rem below; entry headings stack dates beneath titles; skills drop to 2 columns (min 9rem, 1.25rem gap); jump-nav column gap tightens to 1rem.

**Print:** a dedicated print sheet sets the resume in black at 10.5pt with zero page padding, a 26pt name, a 7.5rem rail, static 12pt heads, 11.5pt titles, 12pt section padding with #999 rules, entries kept unbroken, and 9pt between entries. The jump nav, contact section and footer are hidden; header contact buttons print as plain text followed by their URL.

### Named Rules
**The Hanging Head Rule.** Section names live in the margin rail, never above the content on desktop. On desktop they are sticky (1.5rem from the top) and stay with their section while it scrolls; this is CSS only.

## Elevation & Depth

Fully flat. There are no shadows anywhere in the public system. Depth and grouping come from whitespace, the hairline rules between sections, and the type hierarchy. The only filled surfaces are the navy primary button and the pale navy wash of the fallback notice and outline-button hover.

### Named Rules
**The No-Card Rule.** Content never sits in raised or bordered boxes; a rule and whitespace separate sections, not containers.

## Shapes

Square-shouldered and quiet. Buttons and the fallback notice use a small 4px radius; the focus outline carries a 2px radius. Lines are 1px throughout: section rules, button borders, link underlines and the drawn nav underline. The only icon is a small northeast arrow drawn as an inline SVG mask in currentColor (stroke 1.6, about 0.95em) trailing each contact button label.

## Components

### Buttons (contact actions)
Plain, confident, and rare: they appear only in the header contact list and the contact close.
- **Shape:** gently squared (4px radius), 1px navy border, min-height 2.75rem, padding 0.5rem 1.05rem, sans 600 at 1rem, trailing northeast arrow.
- **Primary:** the first link in each contact list is the solid button: navy fill, white text. Its hover deepens fill and border to deep navy.
- **Outline:** every other link in the list is white with navy text and border; hover fills with navy wash.
- **Active:** nudges down 1px.
- **Motion:** background, border and color ease over 160ms, transform over 120ms, on cubic-bezier(0.16, 1, 0.3, 1); only when reduced motion is not requested.

### Navigation (jump links)
- **Style:** slate sans 600 at 0.9375rem, no underline at rest, 0.35rem vertical padding.
- **Hover:** text darkens to ink and a 1px underline draws in from the left (background-size transition, 260ms on the same ease-out curve; reduced-motion safe).

### Links
- **Body links:** navy with a 1px underline offset 0.2em.
- **Linked entry titles:** ink text with a navy-line underline at rest; on hover the text and underline turn navy.

### Entry (signature)
The line item that defines the page: serif title, sans 600 subtitle (organization in ink, location in slate after a comma), right-aligned tabular date range, a description paragraph at 65ch, and an optional skills-used run.

### Skills-used run
A quiet typed run in slate at 0.9375rem, items separated by a separator-gray middle dot with 0.5em spacing. It is text, not chips.

### Fallback notice
A status line shown only when live data is unavailable: navy-wash background, navy-line 1px border, 4px radius, 0.8rem by 1rem padding, ink text at line-height 1.5.

### Focus and selection
- **Focus-visible:** 2px solid navy outline, offset 3px, 2px radius, on every focusable element.
- **Selection:** navy background with white text.

## Do's and Don'ts

### Do:
- **Do** keep the public ground pure white (paper) and set text in ink and slate only.
- **Do** reserve navy for links, contact actions, focus and selection.
- **Do** place section heads in the 11rem rail with a hairline rule above each section, sticky on desktop, static at 1.625rem under 48rem.
- **Do** make the first link in each contact list the solid navy button and every other link outlined.
- **Do** set dates in tabular lining figures and keep them on one line.
- **Do** list skills as plain text (multi-column list or a middle-dot run).
- **Do** keep motion to color, underline-draw and a 1px press, gated behind prefers-reduced-motion: no-preference.
- **Do** keep the print sheet in step with any structural change to the page.

### Don't:
- **Don't** put content in cards, panels or shadowed boxes.
- **Don't** render skills or tags as pills or chips.
- **Don't** introduce a second accent color or tint the page ground.
- **Don't** add small uppercase labels or kickers above headings; section names in the rail are the only labels.
- **Don't** apply this system to the admin pages, or the admin teal-on-gray look to the public page.
