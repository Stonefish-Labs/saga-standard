# 15. Audit and Observability

Audit logging provides the evidentiary foundation for security operations, incident response, and compliance in agentic secret management systems. Specifically, audit logging enables:

- **Detection of progressive credential harvesting** -- identifying patterns where an agent accumulates secrets across sessions via write-back ([TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios))
- **Reconstruction of delegation chains** -- tracing cascading agent delegation that could cause unaudited access ([TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios))
- **Identification of tool substitution** -- detecting when agent-authored tools request secrets from unregistered processes ([TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios))
- **Detection of approval fatigue exploitation** -- recognizing patterns of rapid or batched approval requests designed to exhaust human vigilance ([TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios))
- **Investigation of token replay** -- correlating access events when a valid token is obtained via memory, logs, or network interception ([TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios))

This section specifies the audit requirements, entry structure, event taxonomy, storage requirements, and observability capabilities for conformant implementations.

## 15.1 Audit Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-1 | MUST | Every secret access (read, write, delete) **MUST** be logged | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-2 | MUST | Every denied access attempt **MUST** be logged, including failed authentication and failed authorization | [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-3 | MUST | Each audit entry **MUST** include: timestamp (UTC), profile name, token identity (partial), token name, action, and result | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-4 | MUST | Each audit entry for access operations **MUST** include the list of entry keys accessed or requested | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-5 | MUST NOT | Audit entries **MUST NOT** include secret values for entries with `sensitive=true`. Entries with `sensitive=false` **MAY** have their values included at the implementation's discretion | -- |
| AUDIT-6 | MUST | The audit log **MUST** be append-only. Implementations **MUST NOT** provide any interface for modifying or deleting audit entries except through a documented, human-authorized log rotation or archival process | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-7 | SHOULD | The audit log **SHOULD** support structured queries by profile, token identity, action type, and time range (see [§15.7](#157-query-capabilities)) | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-8 | SHOULD | The audit log **SHOULD** support export to external Security Information and Event Management (SIEM) systems (see [§15.8](#158-siem-integration)) | -- |

## 15.2 Audit Entry Structure

The audit entry structure defines the canonical fields for all audit events. Implementations **MUST** include all required base fields in every audit entry. Operation-specific and delegation fields are conditionally required based on the event type.

### Base Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 | Yes | When the event occurred (UTC) |
| `event_type` | String | Yes | Event category: `access`, `lifecycle`, or `delegation` (see [§15.3](#153-event-taxonomy)) |
| `profile_name` | String | Yes | Which profile was accessed or affected |
| `token_id` | String | Yes | Token identifier (partial -- first 8 characters). `"unknown"` if the token could not be identified |
| `token_name` | String | Yes | Human-readable token name. `null` if the token could not be identified |
| `action` | String | Yes | Specific action (see [§15.3](#153-event-taxonomy)) |
| `result` | String | Yes | `"success"` or `"failure"` |
| `source_process` | String | No | Process identity that made the request (path, PID, or equivalent platform identifier) |
| `error` | String | No | Error code if `result` is `"failure"` |

### Access Operation Fields

These fields are required when `event_type` is `access`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entries_accessed` | List[String] | Yes | Which entry keys were accessed or requested |
| `session_id` | String | No | Session ID if access used cached session approval |
| `approval_method` | String | Yes | Approval method used: `auto`, `session`, `interactive`, or `none` (for denied requests where no approval method was evaluated) |

### Write Operation Fields

These fields are additionally required for write and delete actions:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `write_policy` | String | Yes | Write policy that governed the operation: `auto`, `same`, `deny`, `prompt_always` |

### Lifecycle Event Fields

These fields are required when `event_type` is `lifecycle`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `acting_principal` | String | Yes | Identity of the human principal or system that initiated the event |
| `refresh_provider` | String | No | Refresh provider type (e.g., `oauth2`) -- required for refresh events |

### Delegation Fields

These fields are required when the access involves a delegation chain (see [§12 Delegation](../part-3-architecture/12-delegation.md)):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `delegation_token_id` | String | Yes | Delegation token identifier |
| `parent_token_id` | String | Yes | Parent token in the delegation chain |
| `chain_depth` | Integer | Yes | Depth in the delegation chain (1 = direct principal-issued token, 2+ = delegated) |
| `originating_principal` | String | Yes | Human principal who authorized the root of the chain |

### Field Validation

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-9 | MUST | Implementations **MUST** validate all fields written to the audit log against their declared types and reject or sanitize values that do not conform. Field values **MUST** be constrained to maximum lengths appropriate to their type | [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-10 | MUST NOT | Implementations **MUST NOT** interpret or execute content from audit log field values. Audit log consumers (query interfaces, SIEM exporters) **MUST** treat all field values as untrusted data | -- |

> **Design note:** Field validation prevents log injection attacks. A malicious tool could craft a `token_name` or `source_process` containing control characters, ANSI escape sequences, or oversized strings designed to corrupt the log, confuse SIEM parsers, or inject false entries. Treating all field values as untrusted data is the correct default.

## 15.3 Event Taxonomy

Actions follow a consistent namespaced format: `<operation>:<outcome>`. This taxonomy covers all auditable events required by this standard, including access operations ([§9](../part-3-architecture/09-access-control.md), [§10](../part-3-architecture/10-approval-policies.md)), lifecycle events ([§11](../part-3-architecture/11-secret-lifecycle.md)), and delegation events ([§12](../part-3-architecture/12-delegation.md)).

### Access Events (`event_type: "access"`)

| Action | Description |
|--------|-------------|
| `read:auto_approved` | Read access granted by `auto` policy |
| `read:session_approved` | Read access granted by cached session approval |
| `read:approved` | Read access granted by interactive approval |
| `read:denied` | Read access denied (invalid token, unauthorized profile, or user denial) |
| `write:auto_approved` | Write granted by `auto` write policy |
| `write:session_approved` | Write granted by cached session approval |
| `write:approved` | Write granted by interactive approval |
| `write:denied` | Write denied by policy or user denial |
| `delete:auto_approved` | Delete granted by `auto` write policy |
| `delete:session_approved` | Delete granted by cached session approval |
| `delete:approved` | Delete granted by interactive approval |
| `delete:denied` | Delete denied by policy or user denial |

### Lifecycle Events (`event_type: "lifecycle"`)

| Action | Description | Reference |
|--------|-------------|-----------|
| `token:created` | A new token was generated and assigned to a profile | [TOKEN-26](../part-3-architecture/09-access-control.md#95-token-lifecycle) |
| `token:revoked` | A token was revoked by the human principal | [TOKEN-26](../part-3-architecture/09-access-control.md#95-token-lifecycle) |
| `token:expired` | A token expired due to TTL | [TOKEN-26](../part-3-architecture/09-access-control.md#95-token-lifecycle) |
| `profile:created` | A new secret profile was created | [PROV-2](../part-3-architecture/11-secret-lifecycle.md#111-provisioning) |
| `profile:deleted` | A secret profile was deleted | -- |
| `entry:provisioned` | One or more entries were provisioned into a profile | [PROV-2](../part-3-architecture/11-secret-lifecycle.md#111-provisioning) |
| `entry:refreshed` | An entry was refreshed by a Guardian-managed refresh provider | [GREF-5](../part-3-architecture/11-secret-lifecycle.md#113-guardian-managed-refresh) |
| `entry:refresh_failed` | A Guardian-managed refresh attempt failed | [GREF-5](../part-3-architecture/11-secret-lifecycle.md#113-guardian-managed-refresh) |
| `session:created` | A session approval cache was created for a profile | [SESS-1](../part-3-architecture/10-approval-policies.md#103-session-approval-cache) |
| `session:expired` | A session approval cache expired | [SESS-1](../part-3-architecture/10-approval-policies.md#103-session-approval-cache) |
| `session:revoked` | A session approval cache was explicitly revoked by the human principal | [SESS-1](../part-3-architecture/10-approval-policies.md#103-session-approval-cache) |
| `log:rotated` | Audit entries were removed due to retention policy expiry | [AUDIT-17](#156-log-retention) |

### Delegation Events (`event_type: "delegation"`)

| Action | Description | Reference |
|--------|-------------|-----------|
| `delegation:created` | A delegation token was issued | [DEL-8](../part-3-architecture/12-delegation.md#122-delegation-requirements) |
| `delegation:access` | A delegated access request was processed | [DEL-8](../part-3-architecture/12-delegation.md#122-delegation-requirements) |
| `delegation:revoked` | A delegation token was revoked (cascade or explicit) | [DEL-8](../part-3-architecture/12-delegation.md#122-delegation-requirements) |
| `delegation:denied` | A delegation request was denied (scope violation, chain depth exceeded, expired) | [DEL-8](../part-3-architecture/12-delegation.md#122-delegation-requirements) |

## 15.4 Example Audit Entries

> **Non-normative.** The following examples illustrate conformant audit entries. The canonical audit entry structure is defined in [§15.2](#152-audit-entry-structure). Specific serialization formats and field ordering are implementation-defined; example wire-level representations are provided in [Annex A](annex-a-protocol-details.md).

### Successful Read with Session Approval

```json
{
  "timestamp": "2026-02-16T14:32:15.123Z",
  "event_type": "access",
  "profile_name": "aws-production",
  "token_id": "a1b2c3d4",
  "token_name": "deploy-bot",
  "action": "read:session_approved",
  "result": "success",
  "entries_accessed": ["access_key_id", "secret_access_key"],
  "approval_method": "session",
  "session_id": "sess_abc123",
  "source_process": "/usr/bin/deploy-tool"
}
```

### Denied Access (Invalid Token)

```json
{
  "timestamp": "2026-02-16T14:35:22.456Z",
  "event_type": "access",
  "profile_name": "aws-production",
  "token_id": "unknown",
  "token_name": null,
  "action": "read:denied",
  "result": "failure",
  "entries_accessed": [],
  "approval_method": "none",
  "error": "invalid_token"
}
```

### Write with Interactive Approval

```json
{
  "timestamp": "2026-02-16T14:40:01.789Z",
  "event_type": "access",
  "profile_name": "oauth-google",
  "token_id": "e5f6g7h8",
  "token_name": "sync-service",
  "action": "write:approved",
  "result": "success",
  "entries_accessed": ["access_token"],
  "approval_method": "interactive",
  "write_policy": "prompt_always",
  "source_process": "/opt/sync/bin/syncer"
}
```

### Delegated Access

```json
{
  "timestamp": "2026-02-16T15:10:33.901Z",
  "event_type": "delegation",
  "profile_name": "aws-production",
  "token_id": "d9e0f1a2",
  "token_name": "sub-agent-deploy",
  "action": "delegation:access",
  "result": "success",
  "entries_accessed": ["access_key_id"],
  "approval_method": "session",
  "delegation_token_id": "del_x1y2z3",
  "parent_token_id": "a1b2c3d4",
  "chain_depth": 2,
  "originating_principal": "admin@example.com"
}
```

### Token Lifecycle Event

```json
{
  "timestamp": "2026-02-16T09:00:00.000Z",
  "event_type": "lifecycle",
  "profile_name": "aws-production",
  "token_id": "a1b2c3d4",
  "token_name": "deploy-bot",
  "action": "token:created",
  "result": "success",
  "acting_principal": "admin@example.com"
}
```

## 15.5 Audit Log Storage and Protection

### Trust Model

Audit logs are owned by the Guardian and readable by the human principal and personnel authorized by the human principal. The Guardian **MUST NOT** provide audit log access to agents or tools through the secret access protocol. Audit log access **SHOULD** be managed through a separate administrative interface, independent of the secret request channel, with access authorization controlled by the human principal.

### Storage Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-11 | SHOULD | Audit logs **SHOULD** be stored in a structured, machine-parseable format (e.g., JSON Lines, structured database with append-only semantics, or structured system logging) | -- |
| AUDIT-12 | MUST | Access controls **MUST** restrict audit log read and write access to the Guardian process identity and authorized administrative principals. The mechanism is platform-dependent (e.g., file permissions on Unix, ACLs on Windows, IAM policies in cloud environments). Agents and tools **MUST NOT** have read or write access to audit logs | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-13 | MUST | Audit logs **MUST** be stored in a Guardian-controlled location. The storage path or mechanism **MUST NOT** be configurable by agents or tools | [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Tamper Evidence

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-14 | SHOULD | At Level 2 and above, audit logs **SHOULD** be tamper-evident. Implementations satisfying this requirement **MUST** use one or more of the following mechanisms: (a) hash chaining -- each entry includes an HMAC computed over the concatenation of the previous entry's HMAC and the current entry's canonical serialization, using a Guardian-held audit integrity key and an algorithm approved in [§14 Cryptographic Requirements](14-cryptographic-requirements.md) (e.g., HMAC-SHA256); (b) periodic cryptographic signatures over log segments using a signing key approved in [§14](14-cryptographic-requirements.md); (c) write-once storage (WORM); or (d) real-time replication to an external log aggregation system | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-15 | MUST | At Level 3, audit logs **MUST** be tamper-evident using at least one mechanism specified in AUDIT-14 | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

> **Design note:** Hash chaining initialization: the first entry in a new audit log **SHOULD** use a well-known sentinel value (e.g., 32 zero bytes) as the "previous HMAC" input. The audit integrity key **MUST** be distinct from the master encryption key used for secret storage. Key management for the audit integrity key follows the same requirements as the master key ([§14.2](14-cryptographic-requirements.md#142-master-key-management)).

## 15.6 Log Retention

| ID | Level | Requirement |
|----|-------|-------------|
| AUDIT-16 | MUST | Implementations **MUST** support configurable retention periods per profile |
| AUDIT-17 | MUST | When audit entries are removed due to retention expiry, the removal **MUST** be recorded as a lifecycle event (`log:rotated`) with the time range of removed entries and the acting principal or automated policy that triggered the removal |

> **Non-normative.** The following retention recommendations reflect common compliance and operational needs. Deployers **SHOULD** align retention periods with applicable regulatory and organizational requirements.

| Profile Type | Recommended Minimum | Rationale |
|--------------|---------------------|-----------|
| Production credentials | 90 days | Sufficient for most incident investigation timelines |
| Development credentials | 30 days | Lower risk; shorter retention reduces storage burden |
| High-value credentials (Level 3) | 1 year | Regulatory requirements (PCI-DSS, HIPAA, SOC 2) commonly mandate 1-year retention |

Deployers should also consider local regulatory requirements, industry-specific standards, incident investigation timelines, and storage constraints when setting retention policies.

## 15.7 Query Capabilities

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-18 | SHOULD | Implementations **SHOULD** support filtering audit entries by profile name within a specified time range | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-19 | SHOULD | Implementations **SHOULD** support filtering audit entries by token identity (name or partial `token_id`) within a specified time range | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-20 | SHOULD | Implementations **SHOULD** support filtering audit entries by action type (including denied attempts) within a specified time range | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-21 | SHOULD | Implementations **SHOULD** support filtering audit entries by arbitrary start and end timestamps | -- |
| AUDIT-22 | SHOULD | Implementations **SHOULD** support filtering audit entries by event type (`access`, `lifecycle`, `delegation`) | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

Query interfaces and syntax are implementation-defined. Example wire-level query patterns for implementations that expose audit queries through the Guardian protocol are provided in [Annex A](annex-a-protocol-details.md).

## 15.8 SIEM Integration

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-23 | SHOULD | At Level 2 and above, implementations **SHOULD** support export of audit entries to external SIEM systems via at least one of: (a) webhook delivery -- each audit entry POSTed to a configured HTTPS endpoint; (b) structured file export -- audit entries written to a file in a format compatible with standard log forwarders; or (c) direct integration via a documented, standards-based event ingestion API | -- |
| AUDIT-24 | MUST | At Level 3, implementations **MUST** support SIEM export via at least one mechanism specified in AUDIT-23 | -- |
| AUDIT-25 | SHOULD | Implementations that support SIEM export **SHOULD** map audit entry fields to an established event schema -- such as the Open Cybersecurity Schema Framework (OCSF), Common Event Format (CEF), or an equivalent structured schema -- to enable correlation with events from other security tools | -- |
| AUDIT-26 | MUST | SIEM export mechanisms **MUST** use authenticated, encrypted transport (TLS 1.3 or later per [§14](14-cryptographic-requirements.md)) for webhook and API-based delivery | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Delivery Models

Implementations **MAY** support one or more of the following delivery models:

```
Webhook:    Guardian → HTTPS POST → SIEM endpoint
File:       Guardian → Structured log file → Log forwarder → SIEM
API:        Guardian → Event ingestion API → SIEM
```

> **Non-normative.** Common log forwarders include agents that monitor structured log files and forward entries to centralized systems. Common event ingestion APIs include HTTP-based event collectors and cloud-native log ingestion endpoints. Implementations **SHOULD** document which delivery models and forwarder integrations are supported.

## 15.9 Anomaly Detection

This section defines the normative anomaly detection requirements referenced by [§13.4 Level 3 (CONF-L3-4)](../part-4-conformance/13-conformance.md#134-level-3-advanced). Anomaly detection enables identification of approval fatigue exploitation ([TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios)), token replay ([TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios)), and progressive credential harvesting ([TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios)).

### Detection Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| ANOM-1 | MUST | At Level 3, implementations **MUST** detect access frequency exceeding a configurable threshold per profile per time window (e.g., more than N accesses to profile P within T minutes). Thresholds **MUST** be configurable by the human principal | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-2 | MUST | At Level 3, implementations **MUST** detect access from previously unseen transport endpoints (new source IP address, new Unix socket peer, or equivalent transport-level identifier) | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-3 | MUST | At Level 3, implementations **MUST** detect access outside configured time-of-day windows. Time windows **MUST** be configurable per profile | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-4 | SHOULD | Implementations **SHOULD** detect rapid sequential approval patterns -- multiple approval requests within a short time window (configurable, default not exceeding 60 seconds between requests) -- and flag these for review | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-5 | SHOULD | Implementations **SHOULD** detect access to profiles that have not been accessed within a configurable lookback period (e.g., 30 days) | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-6 | MAY | Implementations **MAY** use statistical, heuristic, or machine-learning methods for additional anomaly detection beyond the minimum requirements of ANOM-1 through ANOM-3. Such methods **MUST** be documented and their detection criteria **MUST** be configurable | -- |

### Alerting

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| ANOM-7 | MUST | At Level 3, detected anomalies **MUST** generate alerts delivered to the human principal or a designated security contact through at least one configurable channel (e.g., webhook to an incident response system, authenticated messaging integration, email, or SIEM correlation) | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-8 | MUST | At Level 3, each alert **MUST** include: the anomaly type (referencing ANOM-1 through ANOM-6), the profile name, the triggering event details (token identity, timestamp, action), and the detection threshold or rule that was violated | -- |
| ANOM-9 | SHOULD | Alert delivery channels **SHOULD** be independent of the agent process -- the agent **MUST NOT** have the ability to suppress, modify, or intercept anomaly alerts | [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

## 15.10 Relationship to Existing Standards

The audit requirements in this section are complementary to -- not replacements for -- established audit and logging standards. Implementations operating in regulated or enterprise environments **SHOULD** consider alignment with:

- **NIST SP 800-92** (Guide to Computer Security Log Management) -- for log management lifecycle, including generation, transmission, storage, and disposal
- **OCSF** (Open Cybersecurity Schema Framework) -- for structured event schemas that enable cross-tool correlation in SIEM environments
- **RFC 5424** (The Syslog Protocol) -- for implementations using system logging infrastructure

See [§16 Relationship to Existing Standards](16-relationship-to-standards.md) for the broader standards landscape.

---

Next: [Relationship to Existing Standards](16-relationship-to-standards.md)
