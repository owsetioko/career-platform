# Personal Resume Platform Implementation Plan

Status: Implementation complete locally; Azure VM deployment remains future work

This plan translates the approved product specification into a beginner-friendly delivery approach for a working MVP that can grow into a larger career platform.

The agreed MVP stack is Python, FastAPI, Jinja2 templates, SQLite, and plain CSS. Develop and test locally in GitHub Codespaces first; Azure VM hosting is a later step.

## 1. Goals of the implementation

Build a database-backed personal resume and portfolio site that:

- presents a clear professional profile to recruiters
- stores content in structured records
- allows easy updates without code changes
- uses a clean architecture that can later support more features

## 2. Recommended stack

The selected MVP stack is:

- Backend/API: Python + FastAPI
- Template rendering: Jinja2 templates
- Database: SQLite
- Styling: plain CSS
- Hosting: local Codespace first, then Azure VM later
- Authentication: single-owner Argon2 password verification, signed sessions, and CSRF protection for admin forms

This stack is easy to run locally. SQLite stores the MVP data in a local file. For the documented Azure VM option, keep that file and the public-profile fallback snapshot on persistent storage, and run one app worker; this SQLite setup is not intended for multiple app servers.

## 3. Core architecture

The application should be split into these layers:

### 3.1 Public site layer
This is the recruiter-facing experience.

Responsibilities:
- render public profile page
- show experience, skills, projects, and education
- expose SEO metadata and structured content
- support mobile and desktop layouts

### 3.2 Data layer
This is where structured content lives.

Main tables:
- profiles
- experiences
- skills
- projects
- education
- maybe tags or categories later

This allows dynamic rendering from the database instead of hardcoded copy.

### 3.3 Admin layer
This is the editing experience for the site owner.

Responsibilities:
- create/update/delete content records
- order items for display
- manage links and metadata
- secure access to admin pages

### 3.4 Request and data-handling layer
FastAPI handles browser requests, validates admin forms, and reads/writes the database.

Responsibilities:
- fetch public profile data
- accept admin data updates
- validate input before writing to the database

## 4. MVP feature scope

### Public pages
- home/profile page
- recruiter-friendly summary and hero section
- work experience section
- skills section
- projects section
- education section
- contact section

### Admin features
- login to secure content management
- ability to create/edit/delete records
- ability to set display order
- ability to hide or show sections

## 5. Suggested project structure

The implementation uses a Python-oriented structure:

- `app/` — FastAPI routes, database models, and application logic
- `app/templates/` — Jinja2 page templates
- `app/static/css/` — plain CSS
- `tests/` — automated tests
- `data/` — ignored local SQLite database and last-known-good public profile snapshot
- `.env` — local settings and secrets; never commit this file

## 6. Database design

### profiles
- id
- full_name
- headline
- summary
- location
- email
- website_url
- linkedin_url
- github_url
- created_at
- updated_at

### experiences
- id
- profile_id
- company_name
- role_title
- start_date
- end_date
- is_current
- location
- description
- achievements
- order_index

### skills
- id
- profile_id
- name
- category
- proficiency_level
- display_order

### projects
- id
- profile_id
- title
- short_description
- full_description
- project_url
- repository_url
- start_date
- end_date
- featured
- tags
- impact_summary

### education
- id
- profile_id
- institution_name
- degree_name
- field_of_study
- start_date
- end_date
- description

### optional future tables
- recommendations
- articles
- opportunity_listings
- tags

## 7. Implementation phases

### Phase 1: Setup and foundation
Tasks:
- initialize project
- choose framework and database provider
- set up local dev environment
- configure environment variables
- create project structure
- set up basic styling foundation

Deliverable:
- project runs locally
- app shell is configured

### Phase 2: Data model and database
Tasks:
- create SQLite tables for profile, experience, skills, projects, and education
- add seed data for the initial profile
- validate relationships and required fields
- set up a simple database initialization workflow for local development

Deliverable:
- SQLite database is created and connected to the app
- sample content is visible in the app
- the structure is ready for future migration to PostgreSQL or another database if needed

### Phase 3: Public profile pages
Tasks:
- render hero section
- render summary
- render detailed experience list
- render skills list
- render projects list
- render education list
- render contact section
- add metadata for SEO

Deliverable:
- recruiter-facing site works and displays data from the database

### Phase 4: Admin editing experience
Tasks:
- create login/auth for admin area
- build CRUD pages for profile and core entities
- add validation for required fields
- allow ordering of items
- add preview or refresh workflow

Deliverable:
- user can update site content without editing code

### Phase 5: Security and polish
Tasks:
- secure admin routes
- sanitize content output
- improve responsiveness
- test key flows
- verify performance and accessibility basics

Deliverable:
- production-ready MVP with secure admin access

### Phase 6: Local validation and future Azure VM readiness
Tasks:
- run the full test suite and local HTTP smoke checks
- verify public fallback behavior, admin access, and content editing
- verify environment variables and secrets
- document persistent storage, backups, HTTPS/reverse proxy, firewall, and app restart needs for a future single Azure VM
- handoff instructions for future updates

Deliverable:
- application verified locally in Codespaces
- beginner-friendly Azure VM guidance documented but not deployed

## 8. Milestones

### Milestone 1: App foundation
- project initialized
- database connected
- basic UI runs

### Milestone 2: Content rendering
- all main sections display dynamic data
- sample profile is fully visible

### Milestone 3: Admin management
- content can be updated in the app
- admin login is protected

### Milestone 4: Production-ready MVP
- local application tested and documented
- future Azure VM requirements documented; deployment remains a separate task

## 9. Risks and considerations

### Risk: content model is too rigid
Mitigation:
- design data with reusable fields and future extension in mind

### Risk: admin is too complicated for a beginner
Mitigation:
- keep admin simple and focused on core CRUD actions

### Risk: SEO or layout quality suffers
Mitigation:
- prioritize semantic HTML, metadata, and responsive layout early

### Risk: cloud setup introduces confusion
Mitigation:
- start in Codespaces, explain environment variables clearly, and treat Azure VM setup as a later guided deployment task

## 10. Recommended next steps

1. Review and replace clearly marked profile placeholders with accurate personal details
2. Run locally in Codespaces and verify the browser experience
3. Before Azure deployment, decide the VM size, persistent disk, domain, TLS/reverse proxy, and backup setup
4. Deploy to an Azure VM only as a separate, explicitly approved task

## 11. Beginner-friendly summary

This plan keeps the first version simple but structured. The site will use a database for your profile, work history, skills, and projects; it will display those records on a public page for recruiters; and it will allow you to update the site later through a secure admin interface. The architecture is intentionally flexible so it can evolve into a wider career platform without a major rebuild.
