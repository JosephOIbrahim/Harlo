# Session Lifecycle — Architecture Design

## Data Model

```python
@dataclass
class Session:
    session_id: str          # UUID4, generated on creation
    started_at: int          # Unix timestamp
    last_active: int         # Unix timestamp, updated on each exchange
    exchange_count: int      # Number of exchanges in this session
    domain: str              # Active domain (default "general")
    encoder_type: str        # "lexical" or "semantic"
    closed: bool             # Terminal state flag
    history_json: str        # JSON-serialized conversation history
    allostatic_tokens: int   # Cumulative tokens for load calculation
```

## SessionManager API

```python
class SessionManager:
    def __init__(self, db_path: str, timeout_s: int = 1800):
        """Open/create SQLite sessions table."""

    def create(self, domain="general", encoder_type="semantic") -> Session:
        """Create a new session. Returns Session with fresh UUID."""

    def get(self, session_id: str) -> Session | None:
        """Load session from SQLite. Returns None if not found."""

    def get_or_create(self, session_id: str | None, **kwargs) -> Session:
        """If session_id is None or not found, create new. Otherwise return existing."""

    def update(self, session: Session) -> None:
        """Persist session state back to SQLite."""

    def record_exchange(self, session_id: str, query: str, response: str, tokens: int) -> Session:
        """Record an exchange: bump count, update history, update last_active, accumulate tokens."""

    def close(self, session_id: str) -> Session | None:
        """Mark session closed. Trigger DMN teardown. Return final session state."""

    def close_expired(self, now: int | None = None) -> list[str]:
        """Find and close all sessions past timeout. Returns list of closed session_ids."""

    def list_active(self) -> list[Session]:
        """Return all non-closed, non-expired sessions."""
```

## State Transitions

```
[NEW] --create()--> [ACTIVE] --exchange()--> [ACTIVE]
                    [ACTIVE] --close()-----> [CLOSED]
                    [ACTIVE] --timeout()---> [CLOSED]
                    [CLOSED] (terminal, immutable)
```

## Storage

SQLite table `sessions` in existing `data/twin.db`:
```sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at INTEGER NOT NULL,
    last_active INTEGER NOT NULL,
    exchange_count INTEGER NOT NULL DEFAULT 0,
    domain TEXT NOT NULL DEFAULT 'general',
    encoder_type TEXT NOT NULL DEFAULT 'semantic',
    closed INTEGER NOT NULL DEFAULT 0,
    history_json TEXT NOT NULL DEFAULT '[]',
    allostatic_tokens INTEGER NOT NULL DEFAULT 0
);
```

## Integration Points

1. **Router**: Every command can accept optional `session_id` in args.
   `_handle_ask` looks up session, passes conversation history as context,
   calls `record_exchange` after generation.

2. **AllostasisTracker**: Session's `allostatic_tokens` feeds into
   `AllostasisTracker.record_prompt()` on load. The tracker is ephemeral
   (in-memory per process), but the cumulative token count persists.

3. **DMN Teardown**: `session.close()` calls `dmn_teardown.start()` with
   session context (history, domain, exchange_count).

4. **Config**: `SESSION_TIMEOUT_S` in daemon/config.py, default 1800 (30 min).
   Read from env var `TWIN_SESSION_TIMEOUT`.

## Router Commands

- `session_start` → create session, return session_id
- `session_close` → close session by id
- `session_status` → return session info
- `session_list` → list active sessions
- Existing `ask` handler updated to accept `session_id`

## Conversation History

- Capped at 50 exchanges (100 messages) to bound memory.
- Stored as JSON: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`
- Oldest messages evicted when cap is reached.
