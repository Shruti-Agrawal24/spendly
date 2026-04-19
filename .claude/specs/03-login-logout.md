# Spec: Login and Logout

## Overview

Implement authentication flow by adding login functionality and completing the logout feature. Users should be able to log in with their registered email and password, then log out to end their session. This step introduces session management using Flask's built-in session support, establishing the foundation for protected routes in future steps.

## Depends on

- Step 1 (Database Setup) — requires `users` table and `get_db()` to verify credentials
- Step 2 (Registration) — requires users to exist in the database

## Routes

- `POST /login` — handle login form submission — public
- `GET /logout` — clear session and redirect to landing — logged-in users

## Database changes

No database changes.

## Templates

- **Create:** None
- **Modify:** `templates/login.html` — convert from static page to working login form with email/password fields, CSRF protection, and error display

## Files to change

- `app.py` — add POST route handler for `/login`, implement `/logout`
- `templates/login.html` — add form with email and password fields
- `database/db.py` — add `get_user_by_email(email)` helper function

## Files to create

- None

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries only
- Passwords must be verified with `werkzeug.security.check_password_hash`
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Form must include CSRF token protection
- Use Flask's `session` dict for storing `user_id` after successful login
- Set `session.permanent = True` to persist session beyond browser close
- Display user-friendly error messages for invalid credentials
- On successful login, redirect to `/profile` (Step 4) or `/` with success message
- Use `flash()` for one-time messages between redirects
- Logout must clear `session['user_id']` completely
- Use `session.clear()` on logout to remove all session data

## Definition of done

- [ ] Login form renders with email and password fields
- [ ] Form includes CSRF protection
- [ ] Empty email shows validation error
- [ ] Empty password shows validation error
- [ ] Invalid email/password combination shows "Invalid credentials" error (generic message for security)
- [ ] Valid credentials log user in and store `user_id` in session
- [ ] Successful login redirects to `/` with "Welcome back" success message
- [ ] Logged-in user visiting `/login` redirects to `/` (already logged in)
- [ ] Logout clears session and redirects to `/` with "Logged out successfully" message
- [ ] Password verification uses `check_password_hash` (not plain text comparison)
- [ ] All database queries use parameterized statements (no string formatting)
- [ ] Session is completely cleared on logout (no residual data)
