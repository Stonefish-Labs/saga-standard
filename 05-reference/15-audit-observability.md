# 15. Audit and Observability

Audit logging provides the evidentiary foundation for security operations, incident response, and compliance in agentic secret management systems. Specifically, audit logging enables:

- **Detection of progressive credential harvesting:** identifying patterns where an agent accumulates secrets across sessions via write-back ([TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios))
- **Reconstruction of delegation chains:** tracing cascading agent delegation that could cause unaudited access ([TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios))
- **Identification of tool substitution:** detecting when agent-authored tools request secrets from unregistered processes ([TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios))
- **Detection of approval fatigue exploitation:** recognizing patterns of rapid or batched approval requests designed to exhaust human vigilance ([TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios))
- **Investigation of token replay:** correlating access events when a valid token is obtained via memory, logs, or network interception ([TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios))

This section specifies the audit requirements, entry structure, event taxonomy, storage requirements, and observability capabilities for conformant implementations.

## 15.1 Audit Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-1 | MUST | Every secret access (read, write, delete) **MUST** be logged | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-2 | MUST | Every denied access attempt **MUST** be logged, including failed authentication and failed authorization | [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-3 | MUST | Each audit entry **MUST** include: timestamp (UTC, millisecond precision), profile name, token identity (partial), token name, action, and result | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-3a | MUST | Timestamps **MUST** be formatted as `YYYY-MM-DDTHH:mm:ss.sssZ` (UTC, millisecond precision). Non-UTC offsets and sub-millisecond precision are **NOT** permitted. Consistent timestamp format is required for reliable SIEM correlation | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-4 | MUST | Each audit entry for access operations **MUST** include the list of entry keys accessed or requested | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-5 | MUST NOT | Audit entries **MUST NOT** include secret values for entries with `sensitive=true`. Entries with `sensitive=false` **MAY** have their values included at the implementation's discretion | -- |
| AUDIT-6 | MUST | The audit log **MUST** be append-only. Implementations **MUST NOT** provide any interface for modifying or deleting audit entries except through a documented, human-authorized log rotation or archival process | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-7 | SHOULD | The audit log **SHOULD** support structured queries by profile, token identity, action type, and time range (see [§15.7](#157-query-capabilities)) | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-8 | SHOULD | The audit log **SHOULD** support export to external Security Information and Event Management (SIEM) systems (see [§15.8](#158-siem-integration)) | -- |

## 15.2 Audit Entry Structure

The audit entry structure defines the canonical fields for all audit events. Implementations **MUST** include all required base fields in every audit entry. Operation-specific and delegation fields are conditionally required based on the event type.

### Base Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 UTC ms | Yes | When the event occurred. **MUST** be formatted as `YYYY-MM-DDTHH:mm:ss.sssZ` (UTC, millisecond precision, 'Z' suffix mandatory). Sub-millisecond precision **MUST NOT** be used. Non-UTC offsets are **NOT** accepted. Example: `"2026-02-17T14:32:15.123Z"` |
| `event_type` | String | Yes | Event category: `access`, `lifecycle`, or `delegation` (see [§15.3](#153-event-taxonomy)) |
| `profile_name` | String | Yes | Which profile was accessed or affected |
| `token_id` | String | Yes | Token identifier (partial, first 8 characters). `"unknown"` if the token could not be identified |
| `token_name` | String | Yes | Human-readable token name. `null` if the token could not be identified |
| `action` | String | Yes | Specific action (see [§15.3](#153-event-taxonomy)) |
| `result` | String | Yes | `"success"` or `"failure"` |
| `source_process` | String | Yes | Process identity that made the request (executable path, PID, or equivalent platform identifier). This field is the primary forensic indicator for tool substitution detection ([TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios)). If the Guardian cannot determine the requesting process identity, the value **MUST** be `"unknown"` (not omitted). Implementations **MUST** make a best-effort attempt to populate this field using available OS primitives (e.g., SO_PEERCRED on Linux, peer process info on macOS, process handle on Windows) |
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
| `refresh_provider` | String | No | Refresh provider type (e.g., `oauth2`); required for refresh events |

### Delegation Fields

These fields are required when the access involves a delegation chain (see [§12 Delegation](../03-architecture/12-delegation.md)):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `delegation_token_id` | String | Yes | Delegation token identifier |
| `parent_token_id` | String | Yes | Parent token in the delegation chain |
| `chain_depth` | Integer | Yes | Depth in the delegation chain (1 = direct principal-issued token, 2+ = delegated) |
| `originating_principal` | String | Yes | Human principal who authorized the root of the chain |

### Field Validation

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-9 | MUST | Implementations **MUST** validate all fields written to the audit log against their declared types and reject or sanitize values that do not conform. Field values **MUST** be constrained to maximum lengths appropriate to their type | [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-10 | MUST NOT | Implementations **MUST NOT** interpret or execute content from audit log field values. Audit log consumers (query interfaces, SIEM exporters) **MUST** treat all field values as untrusted data | -- |

> **Design note:** Field validation prevents log injection attacks. A malicious tool could craft a `token_name` or `source_process` containing control characters, ANSI escape sequences, or oversized strings designed to corrupt the log, confuse SIEM parsers, or inject false entries. Treating all field values as untrusted data is the correct default.

## 15.3 Event Taxonomy

Actions follow a consistent namespaced format: `<operation>:<outcome>`. This taxonomy covers all auditable events required by this standard, including access operations ([§9](../03-architecture/09-access-control.md), [§10](../03-architecture/10-approval-policies.md)), lifecycle events ([§11](../03-architecture/11-secret-lifecycle.md)), and delegation events ([§12](../03-architecture/12-delegation.md)).

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
| `token:created` | A new token was generated and assigned to a profile | [TOKEN-26](../03-architecture/09-access-control.md#95-token-lifecycle) |
| `token:revoked` | A token was revoked by the human principal | [TOKEN-26](../03-architecture/09-access-control.md#95-token-lifecycle) |
| `token:expired` | A token expired due to TTL | [TOKEN-26](../03-architecture/09-access-control.md#95-token-lifecycle) |
| `profile:created` | A new secret profile was created | [PROV-2](../03-architecture/11-secret-lifecycle.md#111-provisioning) |
| `profile:deleted` | A secret profile was deleted | -- |
| `entry:provisioned` | One or more entries were provisioned into a profile | [PROV-2](../03-architecture/11-secret-lifecycle.md#111-provisioning) |
| `entry:refreshed` | An entry was refreshed by a Guardian-managed refresh provider | [GREF-5](../03-architecture/11-secret-lifecycle.md#113-guardian-managed-refresh) |
| `entry:refresh_failed` | A Guardian-managed refresh attempt failed | [GREF-5](../03-architecture/11-secret-lifecycle.md#113-guardian-managed-refresh) |
| `session:created` | A session approval cache was created for a profile | [SESS-1](../03-architecture/10-approval-policies.md#103-session-approval-cache) |
| `session:expired` | A session approval cache expired | [SESS-1](../03-architecture/10-approval-policies.md#103-session-approval-cache) |
| `session:revoked` | A session approval cache was explicitly revoked by the human principal | [SESS-1](../03-architecture/10-approval-policies.md#103-session-approval-cache) |
| `log:rotated` | Audit entries were removed due to retention policy expiry | [AUDIT-17](#156-log-retention) |

### Delegation Events (`event_type: "delegation"`)

| Action | Description | Reference |
|--------|-------------|-----------|
| `delegation:created` | A delegation token was issued | [DEL-8](../03-architecture/12-delegation.md#122-delegation-requirements) |
| `delegation:access` | A delegated access request was processed | [DEL-8](../03-architecture/12-delegation.md#122-delegation-requirements) |
| `delegation:revoked` | A delegation token was revoked (cascade or explicit) | [DEL-8](../03-architecture/12-delegation.md#122-delegation-requirements) |
| `delegation:denied` | A delegation request was denied (scope violation, chain depth exceeded, expired) | [DEL-8](../03-architecture/12-delegation.md#122-delegation-requirements) |

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
| AUDIT-12 | MUST | Access controls **MUST** restrict audit log read and write access to the Guardian process identity and authorized administrative principals. The mechanism is platform-dependent (e.g., file permissions on Unix, ACLs on Windows, IAM policies in cloud environments). Agents and tools **MUST NOT** have read or write access to audit logs | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-13 | MUST | Audit logs **MUST** be stored in a Guardian-controlled location. The storage path or mechanism **MUST NOT** be configurable by agents or tools | [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Audit Log Availability Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-13a | MUST | The Guardian **MUST** operate in fail-closed mode with respect to audit log availability. If the audit log becomes unavailable (storage full, write error, or filesystem failure), the Guardian **MUST NOT** continue to grant new secret access requests. The Guardian **MUST** return an error to requesters indicating audit logging is unavailable and **MUST** attempt to record the failure to any available fallback channel (e.g., system journal, stderr, syslog). **In-flight request handling:** Requests that were already partially processed when the audit log became unavailable are treated as follows: (a) if the secret value has not yet been returned to the tool, the Guardian **MUST** deny the request and not release the secret — the partial processing is discarded; (b) if the secret value has already been returned (e.g., in a streaming response), the Guardian **MUST** attempt to write an emergency audit record to any available fallback channel before suspending further operations; in all cases, the Guardian **MUST** resume normal fail-closed behavior for all subsequent requests. The audit log failure and any in-flight request outcomes **MUST** be recorded once audit log availability is restored, if recoverable from fallback records | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-13b | MUST | The Guardian **MUST** emit a WARN-level log entry (to the system logging facility, if the audit log is unavailable) when audit log storage utilization exceeds 80% of configured capacity, to enable proactive remediation before the fail-closed threshold is reached | -- |
| AUDIT-13c | SHOULD | Implementations **SHOULD** support configurable audit log size limits with automated rotation to prevent storage exhaustion. Rotation **MUST** comply with AUDIT-17 (retention event logging) | -- |

### Tamper Evidence

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-14 | MUST | At Level 2 and above, audit logs **MUST** be tamper-evident. Implementations **MUST** use one or more of the following mechanisms: (a) **hash chaining** — each stored entry includes an HMAC computed over the concatenation of the previous entry's chain HMAC and the current entry's canonical serialization (defined in AUDIT-14a), using a Guardian-held audit integrity key with HMAC-SHA256 or a signing algorithm approved in [§14](14-cryptographic-requirements.md); (b) **periodic cryptographic signatures** over log segments using a signing key approved in [§14](14-cryptographic-requirements.md); (c) **write-once storage** (WORM hardware, cloud object storage with object lock, or equivalent); or (d) **real-time replication** to an external log aggregation system outside the Guardian's write access | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-14a | MUST | When hash chaining (AUDIT-14 option a) is implemented, the **canonical serialization** of an audit entry is defined as follows, to ensure all implementations — and external auditors holding the audit integrity key — produce identical hash chain inputs: (1) **Field set:** exactly the base fields defined in §15.2, in the order listed: `timestamp`, `event_type`, `profile_name`, `token_id`, `token_name`, `action`, `result`, `source_process`. The `error` field is included only when present (non-null); absent optional fields are omitted entirely from the canonical form — they are **NOT** included as JSON `null`; (2) **Encoding:** UTF-8 encoding of a JSON object with no insignificant whitespace: no spaces after `:` or `,`, no newlines, no trailing whitespace; (3) **Timestamps:** formatted per AUDIT-3a (`YYYY-MM-DDTHH:mm:ss.sssZ`); (4) **String values:** JSON strings as specified, `null` values represented as JSON `null`; (5) **Genesis sentinel:** the "previous HMAC" input for the first entry in a new audit log chain **MUST** be 32 zero bytes (0x00 × 32), encoded as a 64-character lowercase hexadecimal string for storage purposes. Example canonical form (non-normative): `{"timestamp":"2026-02-17T14:32:15.123Z","event_type":"access","profile_name":"aws-production","token_id":"a1b2c3d4","token_name":"deploy-bot","action":"read:approved","result":"success","source_process":"/usr/bin/deploy-tool"}` | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-14b | MUST | The audit integrity key used for hash chaining or segment signing **MUST** be distinct from the master encryption key used for secret storage. The audit integrity key **MUST** be generated using a CSPRNG at Guardian startup, **MUST** be at least 256 bits, and **MUST** be managed with the same requirements as the master key ([§14.2](14-cryptographic-requirements.md#142-master-key-management)). If the audit integrity key is lost, the hash chain cannot be verified; loss of the key **MUST** be treated as a security event and reported to the human principal | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-15 | MUST | At Level 3, audit logs **MUST** be tamper-evident using at least one mechanism from AUDIT-14 **AND** at least one of the following additional controls that provides tamper-evidence independent of the Guardian's own key material: (a) real-time replication to an external log aggregation system outside the Guardian's write access (AUDIT-14 option d); (b) write-once storage (AUDIT-14 option c). This requirement ensures that Level 3 tamper-evidence cannot be defeated by compromise of the Guardian's audit integrity key alone | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |

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
| AUDIT-18 | SHOULD | Implementations **SHOULD** support filtering audit entries by profile name within a specified time range | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-19 | SHOULD | Implementations **SHOULD** support filtering audit entries by token identity (name or partial `token_id`) within a specified time range | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-20 | SHOULD | Implementations **SHOULD** support filtering audit entries by action type (including denied attempts) within a specified time range | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AUDIT-21 | SHOULD | Implementations **SHOULD** support filtering audit entries by arbitrary start and end timestamps | -- |
| AUDIT-22 | SHOULD | Implementations **SHOULD** support filtering audit entries by event type (`access`, `lifecycle`, `delegation`) | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |

Query interfaces and syntax are implementation-defined. Example wire-level query patterns for implementations that expose audit queries through the Guardian protocol are provided in [Annex A](annex-a-protocol-details.md).

## 15.8 SIEM Integration

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AUDIT-23 | SHOULD | At Level 2 and above, implementations **SHOULD** support export of audit entries to external SIEM systems via at least one of: (a) webhook delivery, where each audit entry is POSTed to a configured HTTPS endpoint; (b) structured file export, where audit entries are written to a file in a format compatible with standard log forwarders; or (c) direct integration via a documented, standards-based event ingestion API | -- |
| AUDIT-24 | MUST | At Level 3, implementations **MUST** support SIEM export via at least one mechanism specified in AUDIT-23 | -- |
| AUDIT-25 | SHOULD | Implementations that support SIEM export **SHOULD** map audit entry fields to an established event schema (such as the Open Cybersecurity Schema Framework (OCSF), Common Event Format (CEF), or an equivalent structured schema) to enable correlation with events from other security tools | -- |
| AUDIT-26 | MUST | SIEM export mechanisms **MUST** use TLS 1.3 or later for all webhook and API-based delivery channels. Server certificates **MUST** be validated against a trusted certificate authority. Self-signed certificates are **NOT** permitted for SIEM export channels unless the certificate is pinned and the pin is managed through a documented operational process | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Delivery Models

Implementations **MAY** support one or more of the following delivery models:

```
Webhook:    Guardian → HTTPS POST → SIEM endpoint
File:       Guardian → Structured log file → Log forwarder → SIEM
API:        Guardian → Event ingestion API → SIEM
```

> **Non-normative.** Common log forwarders include agents that monitor structured log files and forward entries to centralized systems. Common event ingestion APIs include HTTP-based event collectors and cloud-native log ingestion endpoints. Implementations **SHOULD** document which delivery models and forwarder integrations are supported.

## 15.9 Anomaly Detection

This section defines the normative anomaly detection requirements referenced by [§13.4 Level 3 (CONF-L3-4)](../04-conformance/13-conformance.md#134-level-3-advanced). Anomaly detection enables identification of approval fatigue exploitation ([TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios)), token replay ([TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios)), and progressive credential harvesting ([TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios)).

### Detection Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| ANOM-1 | MUST | At Level 3, implementations **MUST** detect access frequency exceeding a configurable threshold per profile per time window (e.g., more than N accesses to profile P within T minutes). Thresholds **MUST** be configurable by the human principal | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-2 | MUST | At Level 3, implementations **MUST** detect access from previously unseen transport endpoints (new source IP address, new Unix socket peer, or equivalent transport-level identifier). **Baseline parameters:** An endpoint is considered "previously seen" if it has successfully completed at least one authenticated request to the Guardian within the preceding 30-day observation window (configurable, RECOMMENDED default: 30 days). The baseline **MUST** be calculated from audit log history on Guardian startup and **MUST** be updated continuously from incoming requests. A newly registered Guardian with fewer than 7 days of audit history **MUST** suppress ANOM-2 alerts but **MUST** log a note in the conformance statement that the observation baseline is below the minimum recommendation. Cloud and container environments where source IPs change frequently (e.g., ephemeral container IPs) **SHOULD** document their endpoint baseline criteria in the conformance statement; implementations **MAY** use higher-level stable identifiers (SPIFFE ID, client certificate subject, or mTLS identity) as the baseline unit instead of IP address when IP-based baselining would produce unacceptable alert fatigue | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-3 | MUST | At Level 3, implementations **MUST** detect access outside configured time-of-day windows. Time windows **MUST** be configurable per profile | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-4 | SHOULD | Implementations **SHOULD** detect rapid sequential approval patterns (multiple approval requests within a short time window, configurable, default not exceeding 60 seconds between requests) and flag these for review | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-5 | SHOULD | Implementations **SHOULD** detect access to profiles that have not been accessed within a configurable lookback period (e.g., 30 days) | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-6 | MAY | Implementations **MAY** use statistical, heuristic, or machine-learning methods for additional anomaly detection beyond the minimum requirements of ANOM-1 through ANOM-3. Such methods **MUST** be documented and their detection criteria **MUST** be configurable | -- |

### Alerting

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| ANOM-7 | MUST | At Level 3, detected anomalies **MUST** generate alerts delivered to the human principal or a designated security contact through at least one configurable channel (e.g., webhook to an incident response system, authenticated messaging integration, email, or SIEM correlation) | [TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-8 | MUST | At Level 3, each alert **MUST** include: the anomaly type (referencing ANOM-1 through ANOM-6), the profile name, the triggering event details (token identity, timestamp, action), and the detection threshold or rule that was violated | -- |
| ANOM-9 | SHOULD | Alert delivery channels **SHOULD** be independent of the agent process. Delivery through channels the agent cannot access (e.g., authenticated webhook to an external service, separate messaging integration, or out-of-band system alert) is **RECOMMENDED** over channels co-resident with the agent | [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ANOM-9a | MUST | The agent process **MUST NOT** have the ability to suppress, modify, or intercept anomaly alerts. Implementations **MUST** ensure that the alert delivery pathway does not pass through any code path accessible to the agent process. If the alert delivery mechanism fails, the failure **MUST** be recorded in the audit log and the Guardian **MUST** attempt delivery through any configured fallback channel | [TS-15](../01-foundations/03-threat-model.md#32-threat-scenarios) |

## 15.10 Relationship to Existing Standards

The audit requirements in this section are complementary to, not replacements for, established audit and logging standards. Implementations operating in regulated or enterprise environments **SHOULD** consider alignment with:

- **NIST SP 800-92** (Guide to Computer Security Log Management): for log management lifecycle, including generation, transmission, storage, and disposal
- **OCSF** (Open Cybersecurity Schema Framework): for structured event schemas that enable cross-tool correlation in SIEM environments
- **RFC 5424** (The Syslog Protocol): for implementations using system logging infrastructure

See [§16 Relationship to Existing Standards](16-relationship-to-standards.md) for the broader standards landscape.

---

Next: [Relationship to Existing Standards](16-relationship-to-standards.md)
