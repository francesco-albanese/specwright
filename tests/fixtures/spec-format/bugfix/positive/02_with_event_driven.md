# Bugfix: Session not invalidated on logout

## Current Behavior

After the user clicks Logout, the cookie is cleared client-side but the server-side session record in Redis remains until its TTL expires (24 hours).

## Expected Behavior

- When the user submits a logout request, the system shall delete the session record in Redis before responding.
- While the session is being deleted, the system shall reject other requests on that session with HTTP 401.

## Unchanged Behavior

- Login still creates a new session with the same TTL.
- Session refresh on long-lived clients continues to work.
- Idle session expiry via TTL still functions for unclosed sessions.
