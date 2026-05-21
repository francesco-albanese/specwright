# Requirements: Audit Logging

## User Stories

- As a compliance officer, I want every state change recorded so that audits succeed.

## Acceptance Criteria

- The system shall write every mutation to the append-only audit log.
- While the audit log writer is offline, the system shall buffer events in memory.
- When buffered events exceed 10 000, the system shall pause mutations.
