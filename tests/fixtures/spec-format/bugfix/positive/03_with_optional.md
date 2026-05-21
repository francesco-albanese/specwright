# Bugfix: Audit log skips events while writer recovers

## Current Behavior

When the disk writer reconnects after an outage, the in-memory buffer is flushed but events accumulated during the reconnection handshake are dropped.

## Expected Behavior

- While the disk writer is reconnecting, the system shall continue buffering events.
- When the disk writer reports ready, the system shall flush the entire buffer in order.
- Where strict mode is enabled, the system shall return an error to the caller if the buffer overflows.

## Unchanged Behavior

- The normal write path bypasses the buffer.
- Buffer overflow without strict mode still drops the oldest entries silently.
