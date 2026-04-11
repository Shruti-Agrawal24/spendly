# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly - A Flask-based expense tracking web application. Students are building this as a guided project with numbered steps.

## Commands

```bash
# Run the application
python app.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture
spendly/
├── app.py # All routes — single file, no blueprints
├── database/
│ └── db.py # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│ ├── base.html # Shared layout — all templates must extend this
│ └── *.html # One template per page
├── static/
│ ├── css/
│ │ ├── style.css # Global styles
│ │ └── landing.css # Landing-page-only styles
│ └── js/
│ └── main.js # Vanilla JS only
└── requirements.txt

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries ('?' placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

## Development Context

This is a student project with implementation steps. Key routes marked as "coming in Step X" are placeholders:
- `/logout` (Step 3)
- `/profile` (Step 4)
- `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` (Steps 7-9)

The database layer (`database/db.py`) is a stub awaiting Step 1 implementation using SQLite with row_factory and foreign keys enabled.

### Where things belong

- New routes → `app.py` only, no blueprints  
- DB logic → `database/db.py` only, never inline in routes  
- New pages → new `.html` file extending `base.html`  
- Page-specific styles → new `.css` file, not inline `<style>` tags  

---

## Implemented vs Stub Routes

| Route                      | Status                                      |
|---------------------------|---------------------------------------------|
| `GET /`                   | Implemented — renders `landing.html`        |
| `GET /register`           | Implemented — renders `register.html`       |
| `GET /login`              | Implemented — renders `login.html`          |
| `GET /logout`             | Stub — Step 3                               |
| `GET /profile`            | Stub — Step 4                               |
| `GET /expenses/add`       | Stub — Step 7                               |
| `GET /expenses/<id>/edit` | Stub — Step 8                               |
| `GET /expenses/<id>/delete` | Stub — Step 9                             |

**Do not implement a stub route unless the active task explicitly targets that step.**

---

## Warnings and Things to Avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template  
- **Never hardcode URLs** in templates — always use `url_for()`  
- **Never put DB logic in route functions** — it belongs in `database/db.py`  
- **Never install new packages mid-feature** without flagging it — keep `requirements.txt` in sync  
- **Never use JS frameworks** — the frontend is intentionally vanilla  
- **`database/db.py` is currently empty** — do not assume helpers exist until implemented  
- **FK enforcement is manual** — SQLite foreign keys are off by default  
  - `get_db()` must run:  
    ```python
    PRAGMA foreign_keys = ON
    ```
    on every connection  
- The app runs on **port 5001**, not Flask default 5000 — don’t change this  