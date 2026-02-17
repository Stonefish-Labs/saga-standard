# Annex A: Protocol Details (Informative)

> **Status:** This annex is informative. It does not carry normative weight. Conformance is assessed against the standard (SAGA-2026-01) alone, not against this annex. Implementations MAY use alternative wire representations provided all normative requirements in the standard are satisfied.
>
> This annex provides one reference wire protocol for implementers. It illustrates *how* a conformant system may implement the *what* defined by the standard. It is not the only valid implementation.

---

## A.1 Wire Protocol

This section defines a reference wire protocol for communication between tools and the Guardian service. It illustrates an implementation of the requirements in the standard (SAGA-2026-01).

### Protocol Overview

The reference wire protocol uses length-prefixed JSON messages over the configured transport (Unix socket, TCP, or TLS):

```
[4 bytes: message length (big-endian)][JSON payload]
```

This format is transport-agnostic, simple to implement, language-independent, and easy to debug.

### Request Format

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | String | Yes | Operation to perform |
| `protocol_version` | Integer | Yes | Protocol version (current: `1`) |
| `profile_name` | String | Yes* | Target profile |
| `token` | String | Yes* | Agent bearer token |
| `key` | String | Conditional | Entry key (for `get_secret`, `set_entry`, `delete_entry`) |
| `value` | String | Conditional | Entry value (for `set_entry`) |
| `data` | Object | Conditional | Full config dict (for `set_config`) |
| `sensitive` | Boolean | No | Sensitivity flag for `set_entry` |
| `request_id` | String | No | Client-generated correlation ID |

*Not required for `ping` and `shutdown` actions.

#### Protocol Versioning

The `protocol_version` field enables forward-compatible evolution:
- Guardians receiving unknown versions SHOULD respond with `malformed_request`
- Response SHOULD include the maximum supported version
- Clients SHOULD fall back to older versions if supported

#### Request ID

When provided, `request_id` MUST be echoed in the response. This supports concurrent request tracking, request/response correlation, and debugging.

### Defined Actions

| Action | Description | Required Fields |
|--------|-------------|-----------------|
| `ping` | Health check | None |
| `get_config` | Read non-sensitive config entries | `profile_name`, `token` |
| `get_secret` | Read single sensitive entry | `profile_name`, `token`, `key` |
| `set_config` | Replace non-sensitive config | `profile_name`, `token`, `data` |
| `set_entry` | Write/update sensitive entry | `profile_name`, `token`, `key`, `value` |
| `delete_entry` | Remove entry from profile | `profile_name`, `token`, `key` |
| `create_profile` | Create new profile | `profile_name`, `token`, `data` |
| `shutdown` | Graceful Guardian shutdown | None (admin only) |

### Response Format

| Field | Type | Description |
|-------|------|-------------|
| `status` | String | `"ok"` or `"error"` |
| `data` | Any | Response payload (action-specific) |
| `error` | String | Error code (if `status` is `"error"`) |
| `message` | String | Human-readable error description |
| `request_id` | String | Echoed from request (if provided) |

**Success response example:**

```json
{
  "status": "ok",
  "data": {
    "region": "us-west-2",
    "endpoint": "https://api.example.com"
  },
  "request_id": "req_abc123"
}
```

**Error response example:**

```json
{
  "status": "error",
  "error": "access_denied",
  "message": "Approval denied by user",
  "request_id": "req_abc123"
}
```

### Error Codes

| Code | Description | Client Action |
|------|-------------|---------------|
| `not_found` | Profile or entry does not exist | Report to user |
| `access_denied` | Approval denied by policy or user | Report to user |
| `invalid_token` | Token missing, malformed, or unrecognized | Check token config |
| `token_expired` | Token has passed expiry | Request new token |
| `invalid_action` | Unrecognized action | Check version compatibility |
| `malformed_request` | Missing fields or invalid structure | Fix request format |
| `write_denied` | Write policy rejected operation | Fall back to read-only |
| `timeout` | Approval dialog timed out | Retry or report |
| `not_initialized` | Vault not set up | Prompt user to initialize |
| `internal_error` | Unexpected server error | Log and retry |

### Message Size Limits

| Limit | Value | Rationale |
|-------|-------|-----------|
| Maximum message size | 10 MB | Prevent resource exhaustion |
| Maximum profile entries | Implementation-defined | Must support ≥1000 |
| Maximum key length | 256 bytes | Reasonable for identifiers |
| Maximum value length | 1 MB | Large tokens/certificates |

Guardians SHOULD reject messages exceeding limits with `malformed_request`.

### Transport Bindings

#### Unix Domain Socket

1. Connect to socket file at configured path
2. Send length-prefixed JSON message
3. Receive length-prefixed JSON response
4. Close connection (one request per connection)

```
Client                          Guardian
  │                                │
  ├──── connect ──────────────────►│
  │                                │
  ├──── [length][JSON request] ───►│
  │                                │
  │◄─── [length][JSON response] ───┤
  │                                │
  ├──── close ────────────────────►│
  │                                │
```

#### TCP/TLS

1. Connect to `host:port` (TLS handshake for `tls://`)
2. Send length-prefixed JSON message
3. Receive length-prefixed JSON response
4. Close connection

**Timeouts:**
- Connection timeout: 5 seconds (SHOULD be configurable)
- Read timeout: 30 seconds (SHOULD be configurable)

#### Connection Reuse

Implementations MAY support connection reuse for multiple requests, but:
- Each request/response is atomic
- No pipelining without explicit protocol extension
- Connection must be closed on error

### Wire Protocol Example Flows

#### Get Config (Auto-Approved)

```
Client → Guardian:
{
  "action": "get_config",
  "protocol_version": 1,
  "profile_name": "aws-production",
  "token": "tok_a1b2c3d4...",
  "request_id": "req_001"
}

Guardian → Client:
{
  "status": "ok",
  "data": {
    "region": "us-west-2",
    "account_id": "123456789012"
  },
  "request_id": "req_001"
}
```

#### Get Secret (Prompt Required)

```
Client → Guardian:
{
  "action": "get_secret",
  "protocol_version": 1,
  "profile_name": "aws-production",
  "token": "tok_a1b2c3d4...",
  "key": "secret_access_key",
  "request_id": "req_002"
}

[Guardian displays native dialog, user approves]

Guardian → Client:
{
  "status": "ok",
  "data": {
    "key": "secret_access_key",
    "value": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  },
  "request_id": "req_002"
}
```

#### Write Denied

```
Client → Guardian:
{
  "action": "set_entry",
  "protocol_version": 1,
  "profile_name": "static-api-key",
  "token": "tok_a1b2c3d4...",
  "key": "api_key",
  "value": "new_key_value",
  "request_id": "req_003"
}

Guardian → Client:
{
  "status": "error",
  "error": "write_denied",
  "message": "Write mode is 'deny' for this profile",
  "request_id": "req_003"
}
```

---

## A.2 Schema Definitions

This section provides JSON Schema definitions for the standard's data structures. These are informative reference schemas. Implementations MAY use alternative field names and encodings provided the normative requirements of the standard are satisfied.

### Secret Profile Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/profile/v1",
  "title": "Secret Profile",
  "type": "object",
  "required": ["name", "entries", "approval_policy"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9][a-zA-Z0-9._-]*$",
      "maxLength": 128,
      "description": "Unique identifier for the profile"
    },
    "description": {
      "type": "string",
      "maxLength": 1024,
      "description": "Human-readable description"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 64
      },
      "description": "Organizational labels for filtering"
    },
    "entries": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/entry"
      },
      "description": "Secret entries in this profile"
    },
    "approval_policy": {
      "$ref": "#/$defs/approval_policy"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Profile creation time (UTC ISO 8601)"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Last modification time (UTC ISO 8601)"
    }
  },
  "$defs": {
    "entry": {
      "type": "object",
      "required": ["key", "sensitive"],
      "properties": {
        "key": {
          "type": "string",
          "maxLength": 256,
          "description": "Unique identifier within profile"
        },
        "value": {
          "type": "string",
          "description": "Secret value (encrypted at rest, not in schema output)"
        },
        "sensitive": {
          "type": "boolean",
          "description": "Sensitivity classification"
        },
        "description": {
          "type": "string",
          "maxLength": 512,
          "description": "Human-readable description"
        },
        "field_type": {
          "type": "string",
          "enum": ["text", "password", "url", "email", "number", "boolean"],
          "description": "UI rendering hint"
        }
      }
    },
    "approval_policy": {
      "type": "object",
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["auto", "prompt_once", "prompt_always"],
          "description": "Read approval mode"
        },
        "session_ttl": {
          "type": "integer",
          "minimum": 0,
          "maximum": 86400,
          "description": "Session cache TTL in seconds"
        },
        "write_mode": {
          "type": "string",
          "enum": ["same", "auto", "deny", "prompt_always"],
          "description": "Write approval mode"
        }
      }
    }
  }
}
```

### Audit Log Entry Schema

> **Note:** The `action` field uses the namespaced taxonomy defined normatively in [§15.3](../part-5-reference/15-audit-observability.md#153-event-taxonomy) (`<operation>:<outcome>` format). This schema reflects that taxonomy.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/audit/v1",
  "title": "Audit Log Entry",
  "type": "object",
  "required": ["timestamp", "event_type", "profile_name", "token_id", "action", "result"],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "When the access occurred (UTC ISO 8601)"
    },
    "event_type": {
      "type": "string",
      "enum": ["access", "lifecycle", "delegation"],
      "description": "Event category (see §15.3)"
    },
    "profile_name": {
      "type": "string",
      "description": "Which profile was accessed"
    },
    "token_id": {
      "type": "string",
      "description": "Token identifier (first 8 chars, or 'unknown')"
    },
    "token_name": {
      "type": ["string", "null"],
      "description": "Human-readable token name"
    },
    "action": {
      "type": "string",
      "description": "Namespaced action (see §15.3 taxonomy)",
      "enum": [
        "read:auto_approved",
        "read:session_approved",
        "read:approved",
        "read:denied",
        "write:auto_approved",
        "write:session_approved",
        "write:approved",
        "write:denied",
        "delete:auto_approved",
        "delete:session_approved",
        "delete:approved",
        "delete:denied",
        "token:created",
        "token:revoked",
        "token:expired",
        "profile:created",
        "profile:deleted",
        "entry:provisioned",
        "entry:refreshed",
        "entry:refresh_failed",
        "session:created",
        "session:expired",
        "session:revoked",
        "log:rotated",
        "delegation:created",
        "delegation:access",
        "delegation:revoked",
        "delegation:denied"
      ]
    },
    "result": {
      "type": "string",
      "enum": ["success", "failure"],
      "description": "Outcome of the operation"
    },
    "entries_accessed": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Which keys were touched (for access events)"
    },
    "approval_method": {
      "type": "string",
      "enum": ["auto", "session", "interactive", "none"],
      "description": "Approval method used (for access events)"
    },
    "session_id": {
      "type": "string",
      "description": "Session ID if session-based approval"
    },
    "write_policy": {
      "type": "string",
      "enum": ["auto", "same", "deny", "prompt_always"],
      "description": "Write policy for write/delete events"
    },
    "acting_principal": {
      "type": "string",
      "description": "Identity of human principal or system (for lifecycle events)"
    },
    "refresh_provider": {
      "type": "string",
      "description": "Refresh provider type (for refresh lifecycle events)"
    },
    "delegation_token_id": {
      "type": "string",
      "description": "Delegation token identifier (for delegation events)"
    },
    "parent_token_id": {
      "type": "string",
      "description": "Parent token in delegation chain"
    },
    "chain_depth": {
      "type": "integer",
      "minimum": 1,
      "description": "Depth in delegation chain"
    },
    "originating_principal": {
      "type": "string",
      "description": "Human principal who authorized root of chain"
    },
    "source_process": {
      "type": "string",
      "description": "Process identity that made the request"
    },
    "error": {
      "type": "string",
      "description": "Error code if result is failure"
    }
  }
}
```

### Token Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/token/v1",
  "title": "Agent Token",
  "type": "object",
  "required": ["token_id", "profile_name", "name", "created_at"],
  "properties": {
    "token_id": {
      "type": "string",
      "description": "Unique identifier (first 8 chars visible)"
    },
    "profile_name": {
      "type": "string",
      "description": "Profile this token grants access to"
    },
    "name": {
      "type": "string",
      "maxLength": 128,
      "description": "Human-readable label"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "When the token was generated"
    },
    "expires_at": {
      "type": "string",
      "format": "date-time",
      "description": "When the token expires (optional)"
    },
    "last_used_at": {
      "type": "string",
      "format": "date-time",
      "description": "When the token was last used"
    }
  }
}
```

### Token File Format

The reference token file format maps profile names to bearer token values. It is a plain text file where each non-empty, non-comment line is a `profile_name=token_value` pair.

**Example `.saga-token` file:**

```
# SAGA token file — keep this file secret (chmod 600)
aws-production=tok_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
github-api=tok_b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0a1
stripe-live=tok_c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0a1b2
```

**File requirements:**
- Location: `.saga-token` in the project directory (or `~/.saga/tokens` for global)
- Permissions: owner read/write only (`0600`)
- Lines beginning with `#` are comments and MUST be ignored
- Empty lines MUST be ignored
- Files found with permissions more permissive than `0600` SHOULD generate a warning

### Delegation Token Schema

> **Note:** The signature field stores the HMAC-SHA256 output as defined in [§14.5.1](../part-5-reference/14-cryptographic-requirements.md#1451-canonical-signed-payload) — lowercase hexadecimal encoding of the digest over the canonical payload.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/delegation/v1",
  "title": "Delegation Token",
  "type": "object",
  "required": [
    "token_id",
    "parent_token_id",
    "profile_name",
    "scope",
    "permissions",
    "issued_at",
    "expires_at",
    "signature"
  ],
  "properties": {
    "token_id": {
      "type": "string",
      "description": "Unique identifier for the delegation"
    },
    "parent_token_id": {
      "type": "string",
      "description": "Token that authorized this delegation"
    },
    "profile_name": {
      "type": "string",
      "description": "Profile this delegation grants access to"
    },
    "scope": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Allowed entry keys (or [\"*\"] for all — NOT RECOMMENDED)"
    },
    "permissions": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["read", "write", "delete"]
      },
      "description": "Allowed actions"
    },
    "issued_at": {
      "type": "string",
      "format": "date-time",
      "description": "When the delegation was created (UTC ISO 8601, second precision)"
    },
    "expires_at": {
      "type": "string",
      "format": "date-time",
      "description": "When the delegation expires (UTC ISO 8601, second precision)"
    },
    "max_uses": {
      "type": "integer",
      "minimum": 1,
      "description": "Maximum uses (omit for unlimited)"
    },
    "signature": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$",
      "description": "HMAC-SHA256 signature by Guardian — lowercase hex, 64 chars (see §14.5.1)"
    }
  }
}
```

**Example delegation token:**

```json
{
  "token_id": "del_x1y2z3a4",
  "parent_token_id": "tok_a1b2c3d4",
  "profile_name": "aws-production",
  "scope": ["access_key_id", "region"],
  "permissions": ["read"],
  "issued_at": "2026-02-17T12:00:00Z",
  "expires_at": "2026-02-17T13:00:00Z",
  "signature": "3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4"
}
```

### Setup Schema (Tool-Declared Profile Schema)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/setup/v1",
  "title": "Profile Setup",
  "type": "object",
  "properties": {
    "description": {
      "type": "string",
      "description": "Profile description"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["key"],
        "properties": {
          "key": {
            "type": "string",
            "description": "Entry key"
          },
          "sensitive": {
            "type": "boolean",
            "default": true
          },
          "description": {
            "type": "string"
          },
          "field_type": {
            "type": "string",
            "enum": ["text", "password", "url", "email", "number", "boolean"]
          },
          "required": {
            "type": "boolean",
            "default": true,
            "description": "Whether value must be provided during setup"
          }
        }
      }
    },
    "approval_policy": {
      "type": "object",
      "properties": {
        "mode": {
          "type": "string",
          "enum": ["auto", "prompt_once", "prompt_always"],
          "default": "prompt_once"
        },
        "session_ttl": {
          "type": "integer",
          "default": 3600
        },
        "write_mode": {
          "type": "string",
          "enum": ["same", "auto", "deny", "prompt_always"],
          "default": "same"
        }
      }
    }
  }
}
```

### Wire Protocol Request Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/request/v1",
  "title": "Wire Protocol Request",
  "type": "object",
  "required": ["action", "protocol_version"],
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "ping",
        "get_config",
        "get_secret",
        "set_config",
        "set_entry",
        "delete_entry",
        "create_profile",
        "shutdown"
      ]
    },
    "protocol_version": {
      "type": "integer",
      "minimum": 1
    },
    "profile_name": {
      "type": "string"
    },
    "token": {
      "type": "string"
    },
    "key": {
      "type": "string"
    },
    "value": {
      "type": "string"
    },
    "data": {
      "type": "object"
    },
    "sensitive": {
      "type": "boolean"
    },
    "request_id": {
      "type": "string"
    }
  }
}
```

### Wire Protocol Response Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://saga-standard.org/schemas/response/v1",
  "title": "Wire Protocol Response",
  "type": "object",
  "required": ["status"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["ok", "error"]
    },
    "data": {
      "description": "Response payload (action-specific)"
    },
    "error": {
      "type": "string",
      "enum": [
        "not_found",
        "access_denied",
        "invalid_token",
        "token_expired",
        "invalid_action",
        "malformed_request",
        "write_denied",
        "timeout",
        "not_initialized",
        "internal_error"
      ]
    },
    "message": {
      "type": "string",
      "description": "Human-readable error description"
    },
    "request_id": {
      "type": "string"
    }
  }
}
```

### Verification Code Format

When verification codes are implemented (see [§4.4](../part-1-foundations/04-core-concepts.md#44-approval-terms), DLG-5), the reference format is:

- **Structure:** Two uppercase alphanumeric segments separated by a hyphen (e.g., `XKCD-7291`)
- **First segment:** 4 uppercase alphabetic characters from a cryptographically secure random source (26^4 = ~456K values)
- **Second segment:** 4 decimal digits from a cryptographically secure random source (10^4 = 10K values)
- **Combined entropy:** ~32 bits — sufficient for session-scoped anti-spoofing (codes are short-lived and single-use within a session)
- **Display:** Code MUST appear in both the Guardian dialog and the tool's standard output simultaneously

Implementations MAY use alternative formats provided they satisfy the entropy requirement in [§4.4](../part-1-foundations/04-core-concepts.md#44-approval-terms) (at least 16 bits of CSPRNG entropy, unique within session scope).

---

## A.3 Example Flows

This section provides detailed examples of common protocol flows. All flows are informative.

### Flow 1: OAuth Token Refresh

The most common write-back scenario: an OAuth token expires and must be refreshed.

```
┌──────────┐                    ┌───────────┐                    ┌───────────┐
│   Tool   │                    │ Guardian  │                    │   Audit   │
└────┬─────┘                    └─────┬─────┘                    └─────┬─────┘
     │                                │                                │
     │ 1. get_secret("access_token")  │                                │
     ├───────────────────────────────►│                                │
     │                                │                                │
     │                                │ Verify token: valid           │
     │                                │ Check approval: session_cached │
     │                                │                                │
     │ 2. Return access_token         │                                │
     │◄───────────────────────────────┤                                │
     │                                │                                │
     │                                │ Log: read:session_approved     │
     │                                ├───────────────────────────────►│
     │                                │ entries: [access_token]        │
     │                                │                                │
     │ 3. Call API with token         │                                │
     ├─────────────────────────────────────────────────────────────►  │
     │                                │                                │
     │ 4. API returns 401             │                                │
     │◄─────────────────────────────────────────────────────────────  │
     │                                │                                │
     │ 5. get_secret("refresh_token") │                                │
     ├───────────────────────────────►│                                │
     │                                │                                │
     │ 6. Return refresh_token        │                                │
     │◄───────────────────────────────┤                                │
     │                                │ Log: read:session_approved     │
     │                                ├───────────────────────────────►│
     │                                │ entries: [refresh_token]       │
     │                                │                                │
     │ 7. OAuth refresh with refresh_token                            │
     ├─────────────────────────────────────────────────────────────►  │
     │                                │                                │
     │ 8. New access_token            │                                │
     │◄─────────────────────────────────────────────────────────────  │
     │                                │                                │
     │ 9. set_entry("access_token", new_token)                        │
     ├───────────────────────────────►│                                │
     │                                │                                │
     │                                │ Verify token: valid            │
     │                                │ Write mode: auto               │
     │                                │ Encrypt & persist              │
     │                                │                                │
     │ 10. Success                    │                                │
     │◄───────────────────────────────┤                                │
     │                                │                                │
     │                                │ Log: write:auto_approved       │
     │                                ├───────────────────────────────►│
     │                                │ entries: [access_token]        │
     │                                │                                │
     │ 11. Retry API with new token   │                                │
     ├─────────────────────────────────────────────────────────────►  │
     │                                │                                │
     │ 12. Success                    │                                │
     │◄─────────────────────────────────────────────────────────────  │
     │                                │                                │
```

**Key points:** Agent never sees any secret value. Token refresh is logged. Write policy (`auto`) allows unattended refresh. New token available for future invocations.

---

### Flow 2: Interactive Approval (Tier 0)

High-security profile requiring approval for every access.

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│   Tool   │     │ Guardian  │     │  Dialog  │     │  Audit   │
└────┬─────┘     └─────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                │                │
     │ 1. get_secret   │                │                │
     │ ("db_password") │                │                │
     ├────────────────►│                │                │
     │                 │                │                │
     │                 │ Verify token   │                │
     │                 │ Approval:      │                │
     │                 │ prompt_always  │                │
     │                 │                │                │
     │                 │ 2. Spawn dialog│                │
     │                 ├───────────────►│                │
     │                 │                │                │
     │                 │                │ Display:       │
     │                 │                │ Profile: prod  │
     │                 │                │ Token: bot     │
     │                 │                │ Code: ABCD     │
     │                 │                │                │
     │ 3. Return code  │                │                │
     │◄────────────────┼────────────────│                │
     │ "Verify: ABCD"  │                │                │
     │                 │                │                │
     │                 │                │ User verifies  │
     │                 │                │ code matches   │
     │                 │                │                │
     │                 │                │ User clicks    │
     │                 │                │ Approve        │
     │                 │                │                │
     │                 │ 4. Approved    │                │
     │                 │◄───────────────┤                │
     │                 │                │                │
     │ 5. Return secret│                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
     │                 │ Log: read:approved              │
     │                 ├─────────────────────────────────►│
     │                 │ entries: [db_password]          │
     │                 │                                 │
```

**Key points:** Every access requires human action. Verification code prevents spoofing. Full audit trail. Maximum visibility, maximum friction.

---

### Flow 3: Write Denied (Read-Only Profile)

Profile configured with `write_mode: deny`.

```
┌──────────┐                    ┌───────────┐                    ┌───────────┐
│   Tool   │                    │ Guardian  │                    │   Audit   │
└────┬─────┘                    └─────┬─────┘                    └─────┬─────┘
     │                                │                                │
     │ 1. get_config()                │                                │
     ├───────────────────────────────►│                                │
     │                                │                                │
     │                                │ Approval: auto                 │
     │                                │                                │
     │ 2. Return config               │                                │
     │◄───────────────────────────────┤                                │
     │                                │                                │
     │                                │ Log: read:auto_approved        │
     │                                ├───────────────────────────────►│
     │                                │                                │
     │ 3. set_entry("api_key", new)   │                                │
     ├───────────────────────────────►│                                │
     │                                │                                │
     │                                │ Write mode: deny               │
     │                                │                                │
     │ 4. Error: write_denied         │                                │
     │◄───────────────────────────────┤                                │
     │                                │                                │
     │                                │ Log: write:denied              │
     │                                ├───────────────────────────────►│
     │                                │ entries: [api_key]             │
     │                                │                                │
     │ 5. Handle error, continue      │                                │
     │    with existing key           │                                │
     │                                │                                │
```

**Key points:** Reads succeed with `auto` approval. Writes unconditionally rejected. Attempt still logged (shows intent). Tool continues with existing value.

---

### Flow 4: Session Approval (Tier 1)

First access prompts; subsequent access uses cached session.

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│   Tool   │     │ Guardian  │     │  Dialog  │     │  Audit   │
└────┬─────┘     └─────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                │                │
     │ 1. First access │                │                │
     ├────────────────►│                │                │
     │                 │                │                │
     │                 │ No session     │                │
     │                 │ Prompt user    │                │
     │                 ├───────────────►│                │
     │                 │                │                │
     │                 │                │ User approves  │
     │                 │◄───────────────┤                │
     │                 │                │                │
     │                 │ Create session │                │
     │                 │ TTL: 1 hour    │                │
     │                 │                │                │
     │ 2. Return secret│                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
     │                 │ Log: read:approved              │
     │                 ├─────────────────────────────────►│
     │                 │ session_id: sess_123            │
     │                 │                                 │
     │                 │ === 30 minutes later ===        │
     │                 │                                 │
     │ 3. Second access│                │                │
     ├────────────────►│                │                │
     │                 │                │                │
     │                 │ Session valid  │                │
     │                 │ No prompt      │                │
     │                 │                │                │
     │ 4. Return secret│                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
     │                 │ Log: read:session_approved      │
     │                 ├─────────────────────────────────►│
     │                 │ session_id: sess_123            │
     │                 │                                 │
     │                 │ === 70 minutes later ===        │
     │                 │                                 │
     │ 5. Third access │                │                │
     ├────────────────►│                │                │
     │                 │                │                │
     │                 │ Session expired│                │
     │                 │ Prompt user    │                │
     │                 ├───────────────►│                │
     │                 │                │                │
```

**Key points:** One prompt per session. TTL controls session duration. All accesses logged with session ID. Expired sessions require re-approval.

---

### Flow 5: Token Revocation

Immediate revocation of access.

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│  Admin   │     │ Guardian  │     │   Tool   │     │  Audit   │
└────┬─────┘     └─────┬─────┘     └────┬─────┘     └────┬─────┘
     │                 │                │                │
     │ 1. Revoke token │                │                │
     ├────────────────►│                │                │
     │                 │                │                │
     │                 │ Mark token     │                │
     │                 │ revoked        │                │
     │                 │                │                │
     │ 2. Confirmed    │                │                │
     │◄────────────────┤                │                │
     │                 │                │                │
     │                 │ Log: token:revoked              │
     │                 ├─────────────────────────────────►│
     │                 │                                 │
     │                 │ === Tool attempts access ===    │
     │                 │                                 │
     │                 │ 3. get_secret                  │
     │                 │◄───────────────┤                │
     │                 │                │                │
     │                 │ Token revoked  │                │
     │                 │                │                │
     │                 │ 4. Error: invalid_token         │
     │                 ├───────────────►│                │
     │                 │                │                │
     │                 │ Log: read:denied                │
     │                 ├─────────────────────────────────►│
     │                 │ error: invalid_token            │
     │                 │                                 │
```

**Key points:** Revocation is immediate. No grace period. All subsequent requests denied. Denial logged for forensics.

---

## A.4 Reference Architectures

This section provides reference architecture diagrams for common deployment patterns.

### A.4.1 Single-Machine Deployment

The most common deployment: all components on the user's workstation.

```
+-----------------------------------------------------------------+
|  User's Machine                                                 |
|                                                                 |
|  +------------------+     +---------------------------+         |
|  | OS Keychain      |     | ~/.saga/                  |         |
|  | (master key)     |     |   vault.db (encrypted)    |         |
|  +--------+---------+     |   guardian.sock (0600)    |         |
|           |               |   guardian.pid            |         |
|           |               |   audit.log               |         |
|           |               +-------------+-------------+         |
|           |                             |                       |
|  +--------+-----------------------------+-------+               |
|  | Guardian Service (PID isolated)              |               |
|  | - Holds master key in memory                 |               |
|  | - Listens on Unix socket                     |               |
|  | - Enforces tokens and approval policies      |               |
|  | - Spawns native approval dialogs             |               |
|  | - Logs all access to audit trail             |               |
|  +-----+-------------+-------------+-----------+               |
|        |             |             |                            |
|        v             v             v                            |
|  +-----------+ +-----------+ +-----------+                      |
|  | Tool A    | | Tool B    | | Tool C    |                      |
|  | (MCP srv) | | (script)  | | (plugin)  |                      |
|  | Profile:  | | Profile:  | | Profile:  |                      |
|  | aws-prod  | | stripe    | | github    |                      |
|  +-----------+ +-----------+ +-----------+                      |
|        |             |             |                            |
|        v             v             v                            |
|  +--------------------------------------------------+          |
|  |  Agent (LLM reasoning loop)                      |          |
|  |  - Orchestrates tools                            |          |
|  |  - NEVER sees secret values                      |          |
|  |  - Receives only tool outputs (results, errors)  |          |
|  +--------------------------------------------------+          |
+-----------------------------------------------------------------+
```

**Characteristics:** Single user, single machine. Unix socket for IPC. OS keychain for master key. Native dialogs for approval. All in one trust domain.

**Typical use:** Development workstations, personal AI assistants, local-first agentic tools.

---

### A.4.2 Containerized Deployment

Running in containerized environments (Docker, Kubernetes).

```
+--- Container 1 (Guardian) ---+   +--- Container 2 (Agent) -----+
|                              |   |                             |
|  Guardian Service            |   |  Agent + Tools              |
|  - Master key from           |   |  - Connect to Guardian      |
|    K8s secret / vault        |   |    via TCP (TLS 1.3)        |
|  - Listen on TCP:9700        |   |  - mTLS client cert         |
|  - Approval via webhook      |   |                             |
|                              |   |                             |
|  /vault/vault.db             |   |  /app/agent                 |
|  /vault/audit.log            |   |  /app/tools                 |
|                              |   |                             |
+-------------+----------------+   +-------------+---------------+
              |                                  |
              |         TLS 1.3 (port 9700)      |
              +----------------------------------+
                         Service Mesh / Network
```

**Characteristics:** Separate containers for Guardian and Agent. TCP/TLS transport. Webhook-based approval. Secrets mounted from orchestrator.

**Typical use:** CI/CD pipelines, containerized services, Kubernetes deployments.

---

### A.4.3 Multi-Machine TCP/TLS Deployment

Guardian and agents on separate machines.

```
+--- Machine A (Guardian Host) ----+      +--- Machine B (Agent Host) -------+
|                                  |      |                                  |
|  saga-server                     |      |  saga-client (client only)       |
|                                  |      |                                  |
|  +--- Guardian Service ---------+|      |  +--- Agent + Tools -------------+|
|  | - Master key in OS keychain  ||      |  | SAGA_URL=tls://A:9700        ||
|  | - Listen: tls://0.0.0.0:9700 ||      |  | SAGA_CA_CERT=/path/ca.pem    ||
|  | - TLS 1.3 server cert        ||      |  | - Uses Vault(profile=...,    ||
|  | - Token auth enforced        ||      |  |     url="tls://A:9700")      ||
|  | - Webhook approval callback  ||      |  | - No server code installed   ||
|  +-------------------------------+|      |  +-------------------------------+|
|                                  |      |                                  |
|  ~/.saga/                        |      |  .saga-token                     |
|    vault.db (encrypted)          |      |    my-api=tok_...                |
|    access.log                    |      |                                  |
+----------------------------------+      +----------------------------------+
          ^                                           |
          |         TLS 1.3 (port 9700)              |
          +------------------------------------------+
```

**Key differences from single-machine:** No Unix socket, no PID file, no auto-start. Client package only on agent host. Server package only on Guardian host. TLS certificates must be provisioned. Approval via webhook (no native dialog across machines).

**Typical use:** Centralized secret management, multiple agent hosts sharing one Guardian, enterprise deployments.

---

### A.4.4 Multi-Agent Delegation

Multiple agents with delegation between them.

```
+-----------------------------------------------------------------+
|                     Human Principal                             |
|                          |                                      |
|                          | Token: admin-agent                   |
|                          v                                      |
|  +------------------------------------------------------------+ |
|  |                    Orchestrator Agent                       | |
|  |                                                            | |
|  |  - Receives high-level task                                | |
|  |  - Delegates subtasks to specialist agents                 | |
|  |  - Has token for: deployment, monitoring, notification     | |
|  |                                                            | |
|  +--+--------------------------+---------------------------+--+ |
|     |                          |                           |    |
|     | Delegation Token         | Delegation Token          |    |
|     | (deployment only)        | (monitoring only)         |    |
|     v                          v                           |    |
|  +--+--------+            +----+-------+                   |    |
|  | Deploy    |            | Monitor     |                   |    |
|  | Agent     |            | Agent       |                   |    |
|  | Token:    |            | Token:      |                   v    |
|  | deploy-   |            | monitor-    |            +-----+--+  |
|  | delegated |            | delegated   |            | Notify  |  |
|  +-----+-----+            +------+------+            | Agent   |  |
|        |                         |                   +---+----+  |
|        v                         v                     |         |
|  +-----+-----+            +------+------+              v         |
|  | Deploy    |            | Monitoring  |        +-----+-----+   |
|  | Tool      |            | Tool        |        | Notify    |   |
|  +-----------+            +------------+         | Tool      |   |
|                                                  +-----------+   |
|                                                                 |
|                          +------------------+                    |
|                          |    Guardian      |                    |
|                          |    Service       |                    |
|                          +------------------+                    |
+-----------------------------------------------------------------+

Audit Trail:
  Orchestrator → Deploy Agent → Deploy Tool → aws-production
  Orchestrator → Monitor Agent → Monitor Tool → monitoring-api
  Orchestrator → Notify Agent → Notify Tool → slack-webhook
```

**Key points:** Each agent has its own token. Delegation tokens are scoped to specific profiles. Full delegation chain in audit trail. No agent sees secrets directly.

---

### A.4.5 High-Availability Deployment

> **Status:** High-availability deployments are an advanced pattern (Level 3+) whose normative requirements are deferred to a future revision of this standard. The following considerations are informative guidance only.

HA deployment involves running multiple Guardian replicas behind a load balancer. Key considerations:

- **Master key distribution:** The master key must be available to all replicas; use a hardware security module (HSM) or cloud KMS accessible to all replica hosts, rather than per-host key storage
- **Session cache replication:** Session approval caches held in Guardian memory must be shared or replicated across replicas; a shared Redis cluster or equivalent in-memory store is a common pattern
- **Audit log centralization:** All replicas must write to a centralized audit log to preserve the complete access record
- **Failover logic:** Load balancer health checks should detect failed replicas and route only to healthy ones; the default-deny principle (§5.5) means a replica that cannot contact the master key source must reject all requests rather than serve stale data

Future revisions of this standard may provide detailed normative guidance for HA deployments. Until then, deployers should consult operational security best practices for distributed secret management systems.

---

## A.5 Approval Dialog Reference

Conformant approval dialogs MUST display the following elements (see [§10.4](../part-3-architecture/10-approval-policies.md#104-approval-channel-requirements) for normative requirements):

```
+--------------------------------------------------+
|  Secret Access Request                           |
|                                                  |
|  Profile: aws-production                         │
|  Token:   deploy-bot (a1b2c3d4)                  │
|                                                  |
│  Entries requested:                              │
│    access_key_id                                 │
│    secret_access_key      (sensitive)            │
│    region                                        │
│                                                  |
│  Verification Code: XKCD-7291                    │
│                                                  |
│  [ Deny ]                          [ Approve ]   │
+--------------------------------------------------+
```

### Anti-Spoofing Requirements

| Requirement | Implementation |
|-------------|----------------|
| Native OS window | Not browser, not terminal |
| Guardian-set title | Not configurable by requester |
| Server-side code | Generated by Guardian, not tool |
| Independent display | Code shown in both dialog and tool output |
| Default deny | No auto-approve on timeout |

---

## A.6 Directory Structure Reference

```
~/.saga/
├── vault.db              # Encrypted secret storage (SQLite)
├── vault.db-wal          # SQLite write-ahead log
├── vault.db-shm          # SQLite shared memory
├── guardian.sock         # Unix domain socket (0600)
├── guardian.pid          # Guardian process ID
├── audit.log             # Audit trail (append-only)
├── sessions.db           # Session cache (optional, encrypted)
└── config.toml           # Configuration (optional)

Project directory:
./.saga-token       # Per-project token mapping
  aws-production=tok_...
  github-api=tok_...
```

---

*This annex is informative. Conformance to SAGA-2026-01 is determined by the normative requirements in the standard, not by adherence to any particular wire format described here.*
