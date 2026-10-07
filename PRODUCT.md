# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: recruiters and hiring managers** screening Chris Owen Setioko for full-time roles (graduation 2027). They arrive from an application, a resume link, or LinkedIn, often skim on a phone, and decide within seconds whether to keep reading and get in touch.
- **Target roles:** business/data analyst, operations/management, and consulting. Content that supports these roles should come first.
- **Secondary: the owner** keeps the profile current through the password-protected `/admin` area, without editing code.

## Product Purpose

A database-driven personal resume site that shows experience, skills, projects, and education in a structured, easy-to-scan way. **Success means a recruiter reaches out.** The site should be designed so it can later grow into a broader career platform, as `docs/specs/personal-resume-platform-spec.md` describes.

## Positioning

The site combines two things for a business-side candidate: real operational leadership (daily operations for a bakery with about 50 staff that supplied four other locations, and head of a 10-person events team) and hands-on technical work. The site itself is evidence of the technical side, because Chris built and deployed it on an Azure Ubuntu VM using FastAPI and SQLite. It is bilingual (English and Bahasa Indonesia), and Chris transferred from Santa Monica College to Loyola Marymount University.

## Operating Context

- Public page at `/`. Its content comes from SQLite through the `owner` profile.
- If the database read fails, the public page falls back to `data/public-profile.json`, or to the bundled starter profile. A status notice tells visitors when that happens.
- The owner edits content at `/admin`. Items can be hidden and reordered.
- Production runs on a single Azure VM (`vm-career-platform`) behind a reverse proxy.

## Capabilities and Constraints

- **Stack (incumbent, binding):** FastAPI, Jinja2 templates, and plain CSS (`app/static/css/styles.css`). **No JavaScript and no CSS frameworks or build step.**
- Every section must handle empty data gracefully. Profiles can be missing any field, and the templates already render empty states.
- Content sections: summary, experience (with linked skills), skills, projects (with skills and tags), education, and contact (email, website, LinkedIn, GitHub).
- Undecided: certifications, testimonials, and the growth features in the spec (jobs, articles, analytics) are not built.

## Evidence on Hand

- Live profile content is in `data/resume.db`. This includes 5 experiences, 12 skills, 3 projects (including this site, linked to GitHub), and 3 education entries with GPAs and coursework.
- **Contact data is currently GitHub only.** Email and LinkedIn are empty. Do not invent them.
- There are no metrics, testimonials, case-study outcomes, or headshot beyond what the profile states. Do not fabricate impact numbers.

## Product Principles

1. **Recruiter in 30 seconds:** who Chris is, what role fits, and how to reach Chris must be clear without scrolling deep.
2. **Lead with analyst, ops, and consulting fit:** order and emphasis serve those roles, not a full chronological dump.
3. **Contact is the conversion:** every design decision should make reaching out easier.
4. **Honest and data-driven:** show only what the database holds. Empty states stay graceful, not padded.
5. **Resilient by default:** the public page must stay readable even in fallback mode.

## Accessibility & Inclusion

The target is WCAG 2.2 AA: contrast, keyboard focus, semantic headings and landmarks, and reflow at 320px.
