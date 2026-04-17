# Spec: Registration

## Overview

Implement the registration functionality that allows new users to create an account in Spendly. This step builds on the database foundation from Step 1 by adding the form handling, validation, and user creation logic. Users should be able to register with a name, email, and password, then be redirected to login after successful registration.

## Depends on

- Step 1 (Database Setup) — requires `users` table and `get_db()` to store new users

## Routes

- `POST /register` — handle registration form submission — public

## Database changes

- No database changes — uses existing `users` table from Step 1

## Templates

- **Modify:** `templates/register.html` — add form with fields for name, email, password; include error display and CSRF protection

## Files to change

- `app.py` — add POST route handler for `/register`
- `templates/register.html` — convert from static page to working form
- `database/db.py` — add `create_user(name, email, password)` helper function

## Files to create

- None

## New dependencies

- No new dependencies

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries only
- Passwords must be hashed with `werkzeug.security.generate_password_hash`
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Form must include CSRF token protection
- Email must be validated for format and uniqueness
- Password must be at least 6 characters
- Display user-friendly error messages for validation failures
- On successful registration, redirect to `/login` with success message
- Use `flash()` for one-time messages between redirects

## Definition of done

- [ ] Registration form renders with name, email, and password fields
- [ ] Form includes CSRF protection
- [ ] Empty fields show validation error
- [ ] Invalid email format shows validation error
- [ ] Duplicate email shows "email already registered" error
- [ ] Password under 6 characters shows validation error
- [ ] Valid registration creates user in database with hashed password
- [ ] Successful registration redirects to `/login` with success message
- [ ] Password is never stored in plain text (verify in database)
- [ ] All database queries use parameterized statements (no string formatting)
