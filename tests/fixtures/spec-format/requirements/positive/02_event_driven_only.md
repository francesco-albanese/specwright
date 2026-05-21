# Requirements: Login Flow

## User Stories

- As a user, I want to log in with email and password so that I can access my account.

## Acceptance Criteria

- When the user submits valid credentials, the system shall issue a session token.
- When the user submits invalid credentials, the system shall return HTTP 401.
- When the session token expires, the system shall require re-authentication.
