# Spec: Profile Page

## Overview

Implement the user profile page that displays account information for logged-in users. This is the first protected route that requires authentication, establishing the pattern for all future logged-in features. The profile page shows the user's name, email, and account creation date, providing a foundation for future profile editing functionality.

## Depends on

- Step 1 (Database Setup) — requires `users` table and `get_user_by_id()` helper
- Step 3 (Login and Logout) — requires working authentication and session management

## Routes

- `GET /profile` — display user profile information — logged-in users only

## Database changes

No database changes.

## Templates

- **Create:** `templates/profile.html` — new template extending `base.html` to display user name, email, and account creation date
- **Modify:** None

## Files to change

- `app.py` — update `/profile` route to render template instead of stub string, add login_required check
- `templates/base.html` — add navigation link to Profile page (visible when logged in)

## Files to create

- `templates/profile.html` — profile page template
- `static/css/profile.css` — profile page specific styles

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw SQLite with parameterized queries only
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- Profile route must check if user is logged in via `session.get("user_id")`
- Redirect unauthenticated users to `/login` with "Please log in" flash message
- Use `get_user_by_id()` from `database/db.py` to fetch current user data
- Display user's full name, email, and account creation date (formatted as "Member since Month YYYY")
- Profile page should include a link to logout
- All internal links use `url_for()` — never hardcoded URLs
- Use semantic HTML (proper heading hierarchy, `<dl>` for profile data or similar)
- Profile styles go in separate `profile.css` file, not inline

## Definition of done

- [ ] Visiting `/profile` while not logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in displays the profile page
- [ ] Profile page shows user's name
- [ ] Profile page shows user's email
- [ ] Profile page shows account creation date formatted as "Member since Month YYYY"
- [ ] Profile page includes logout link/button
- [ ] Navigation in `base.html` includes Profile link (visible when logged in)
- [ ] Profile page extends `base.html`
- [ ] Profile-specific styles are in `static/css/profile.css`
- [ ] All database queries use parameterized statements
- [ ] Profile route uses `get_user_by_id()` helper from `database/db.py`
- [ ] No hardcoded URLs in templates (all use `url_for()`)
