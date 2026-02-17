# 11. Secret Lifecycle

This section addresses the complete credential lifecycle: how secrets are provisioned into the system, how they are maintained during operation, and how they are retired.

- **Provisioning** ([§11.1](#111-secret-provisioning)) -- How secrets enter the system in the first place. The standard defines three provisioning models: human-seeded (manual entry), Guardian-mediated (interactive flows like OAuth authorization code exchange), and programmatic (admin API for automation).

- **Tool-initiated write-back** ([§11.2](#112-write-through-protocol)) -- The tool detects an expired credential, performs the refresh externally, and writes the new value back through the Guardian. The tool requires write access to the profile. This is the general-purpose update mechanism that works for any credential type, including tool-specific auth flows and custom grant types.

- **Guardian-managed refresh** ([§11.4](#114-guardian-managed-refresh)) -- The Guardian detects that a requested credential is expired or approaching expiry, invokes a configured refresh provider to obtain a fresh value, persists it internally, and returns the fresh value to the tool. The tool requires only read access. This eliminates the write attack surface entirely for profiles where the Guardian can perform the refresh.

Guardian-managed refresh is the preferred operational model when applicable. By keeping refresh logic in the trusted component rather than the semi-trusted tool, the write path ([TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios)) is not mitigated -- it is eliminated. The profile's write policy can be set to `deny`, and no tool-initiated write-back is needed. Tool-initiated write-back remains for scenarios where only the tool can perform the refresh (tool-specific authentication flows, custom grant types, refresh operations that require tool-side state).

All lifecycle operations -- provisioning, refresh, write-back, deletion -- enforce the Principle of Write-Through Integrity ([§5.4](../part-2-principles/05-design-principles.md#54-principle-of-write-through-integrity)). All credential changes pass through the Guardian's mediation channel, are encrypted at rest ([§14](../part-5-reference/14-cryptographic-requirements.md)), and are audit-logged ([§15](../part-5-reference/15-audit-observability.md)).

## 11.1 Secret Provisioning

Before secrets can be read, refreshed, or rotated, they must exist. Provisioning -- the initial population of a profile with secret values -- is a bootstrapping problem that the operational lifecycle mechanisms (write-back, Guardian-managed refresh) do not address. A profile with no entries is useless, and tools cannot operate until the secrets they depend on are present.

Provisioning is fundamentally an administrative operation, not a tool operation. Secrets enter the system through channels controlled by the human principal or by authorized provisioning systems -- never through the agent, and never through the tool's runtime API without explicit human authorization.

### Provisioning Models

The standard defines three provisioning models. Implementations **MUST** support human-seeded provisioning. Guardian-mediated and programmatic provisioning are extension points that reduce friction and enable automation while preserving the human principal's authority over secret entry.

#### Human-Seeded Provisioning

The baseline model. The human principal creates a profile and manually enters secret values through the Guardian's administrative interface (CLI, web UI, or equivalent).

| ID | Level | Requirement |
|----|-------|-------------|
| PROV-1 | MUST | Implementations MUST support human-seeded provisioning: the human principal creates a profile and populates entries through the Guardian's administrative interface |
| PROV-2 | MUST | Profile creation and entry population MUST be audit-logged with the acting principal's identity and timestamp ([§15](../part-5-reference/15-audit-observability.md)) |
| PROV-3 | MUST | The human principal MUST set the sensitivity classification for each entry at provisioning time. If no classification is provided, the Guardian MUST default to `sensitive=true` (see [§5.3](../part-2-principles/05-design-principles.md#53-principle-of-declared-sensitivity), SENS-2) |
| PROV-4 | MUST | Secret values entered during provisioning MUST be encrypted immediately upon receipt and MUST NOT be stored in plaintext at any point, including in transit within the administrative interface ([§14](../part-5-reference/14-cryptographic-requirements.md)) |

**When to use:** Static API keys, manually obtained credentials, initial configuration of any profile. This is always available and requires no additional Guardian capabilities.

#### Guardian-Mediated Provisioning

For credential types that are *produced by an interactive flow* -- most notably OAuth authorization code exchange -- the Guardian can orchestrate the provisioning process directly. The human participates in the authorization flow (browser consent screen), but the resulting credentials land in the Guardian without passing through the tool or the agent. This is the natural extension of Guardian-managed refresh ([§11.4](#114-guardian-managed-refresh)): if the Guardian can refresh tokens, it can also obtain them in the first place.

```
┌─────────────────┐    1. Human initiates     ┌───────────┐
│ Human Principal │ ──── provisioning ──────► │ Guardian  │
└─────────────────┘    (via admin interface)   └───────────┘
                                                    │
                       2. Guardian generates        │
                          authorization URL         │
                                                    │
┌─────────────────┐    3. Human authorizes    ┌─────┴───────┐
│ Human Principal │ ──── in browser ────────► │ OAuth       │
└─────────────────┘    (consent screen)       │ Provider    │
                                              └─────┬───────┘
                                                    │
                       4. Callback to Guardian ◄────┘
                          (authorization code)      │
                                                    │
                       5. Guardian exchanges code   │
                          for tokens                │
                       6. Guardian encrypts and     │
                          persists entries          │
                       7. Guardian configures       │
                          refresh provider          │
                       8. Profile ready for use     │
                                              ┌─────┴───────┐
                                              │ Tool reads  │
                                              │ (never      │
                                              │  writes)    │
                                              └─────────────┘
```

| ID | Level | Requirement |
|----|-------|-------------|
| PROV-5 | MAY | Implementations MAY support Guardian-mediated provisioning, where the Guardian orchestrates an interactive credential exchange flow (e.g., OAuth 2.0 authorization code) and populates the profile with the resulting credentials. At Level 2 and above, implementations SHOULD support at least one mediated provisioning flow |
| PROV-6 | MUST | Guardian-mediated provisioning MUST be initiated by the human principal through the Guardian's administrative interface. The agent and tools MUST NOT initiate provisioning flows |
| PROV-7 | MUST | During a mediated provisioning flow, the Guardian MUST receive credential material directly from the external provider (e.g., OAuth callback). Credential material MUST NOT pass through the agent, the tool, or any component outside the Guardian's trust boundary |
| PROV-8 | MUST | Credentials obtained through mediated provisioning MUST be encrypted and persisted immediately upon receipt, consistent with PROV-4 |
| PROV-9 | SHOULD | When a mediated provisioning flow produces credentials that are compatible with Guardian-managed refresh ([§11.4](#114-guardian-managed-refresh)), the implementation SHOULD automatically configure the corresponding refresh provider for the profile. This enables end-to-end Guardian-managed lifecycle: provisioning, refresh, and rotation without tool-initiated writes |
| PROV-10 | MUST | Mediated provisioning flows MUST be audit-logged as a distinct event type, recording: profile name, provisioning flow type (e.g., "oauth2_authorization_code"), the entries populated, and timestamp. Secret values MUST NOT appear in the audit log for entries marked `sensitive=true` ([§15](../part-5-reference/15-audit-observability.md)) |
| PROV-11 | MUST | If a mediated provisioning flow fails (user denies consent, provider returns an error, network failure), the profile MUST NOT be left in a partially populated state. Either all entries produced by the flow are persisted, or none are (consistent with WRITE-3 atomicity) |

**When to use:** OAuth 2.0 authorization code flows, service registration flows, any credential exchange that produces tokens through an interactive human-authorized process. This is the preferred provisioning model for OAuth because it means the tool never needs write access -- from initial provisioning through ongoing refresh, the Guardian manages the credential lifecycle end to end.

#### Programmatic Provisioning

For automated environments (CI/CD pipelines, infrastructure-as-code, cloud provisioners), secrets may be provisioned programmatically through the Guardian's administrative API by authorized provisioning systems.

| ID | Level | Requirement |
|----|-------|-------------|
| PROV-12 | MAY | Implementations MAY support programmatic provisioning through an authenticated administrative API |
| PROV-13 | MUST | The administrative API used for programmatic provisioning MUST be distinct from the tool API. Programmatic provisioners authenticate as administrative principals, not as tools presenting agent tokens. The agent MUST NOT have access to administrative API credentials |
| PROV-14 | MUST | Programmatic provisioning MUST be audit-logged with the provisioning system's identity, the entries populated, and timestamp ([§15](../part-5-reference/15-audit-observability.md)) |
| PROV-15 | SHOULD | Implementations SHOULD support provisioning templates or schemas that define the expected entries for a profile (key names, field types, sensitivity defaults). Templates reduce the risk of misconfiguration and enable validation at provisioning time |

**When to use:** CI/CD pipelines injecting credentials during deployment, infrastructure automation provisioning service accounts, identity providers pushing credentials to the Guardian, any scenario where a trusted system (not a tool, not an agent) needs to populate profiles programmatically.

### Tool-Declared Schema

Tools know what secrets they need. A tool that integrates with GitHub needs `access_token`; a tool that connects to a database needs `host`, `port`, `username`, `password`. Rather than requiring the human principal to know each tool's requirements in advance, the standard supports tool-declared schemas that describe the entries a tool expects.

| ID | Level | Requirement |
|----|-------|-------------|
| PROV-16 | SHOULD | Tools SHOULD publish a machine-readable schema declaring the entries they require: key names, field types ([§8.2](08-secret-profiles.md#82-entry-structure)), recommended sensitivity classifications, and human-readable descriptions. An example schema format is provided in [Annex A](../annexes/annex-a-protocol-details.md) |
| PROV-17 | MAY | Implementations MAY use tool-declared schemas to scaffold profile structure during provisioning -- creating the profile with the correct entry keys, field types, and default sensitivity classifications. The human principal or provisioning system then populates the values |
| PROV-18 | MUST | Tool-declared schemas MUST NOT include default secret values. Schemas declare *structure* (what entries are needed), not *content* (what the values are). A schema that ships with embedded credentials is a supply-chain vulnerability |
| PROV-19 | MUST | The human principal MUST retain the ability to override any schema-suggested configuration, including sensitivity classifications, field types, and whether an entry is required. Schemas are guidance, not mandates |

### What This Prevents

- **Provisioning through untrusted channels:** PROV-6 and PROV-13 ensure that secrets enter the system through administrative channels -- never through the agent, and never through the tool's runtime API without explicit human authorization. This prevents an agent from provisioning credentials it controls into a profile it can later instruct a tool to read.
- **Partial provisioning state:** PROV-11 ensures mediated provisioning flows are atomic. A profile that is half-populated with OAuth tokens but missing the refresh token is a recipe for operational failure and potential security confusion.
- **Schema as attack vector:** PROV-18 prevents tool-declared schemas from being used to inject default credentials. A compromised tool package that ships with a schema containing a backdoor `access_token` value would have that value overwritten during provisioning -- but only if the implementation validates that schemas contain no values.

---

## 11.2 Write-Through Protocol

Write operations follow the same mediation channel as reads, operationalizing the Principle of Write-Through Integrity ([§5.4](../part-2-principles/05-design-principles.md#54-principle-of-write-through-integrity)). The Guardian performs token verification ([§9.3](09-access-control.md#93-token-verification)), evaluates the write approval policy ([§10.2](10-approval-policies.md#102-write-approval-modes)), encrypts the value ([§14](../part-5-reference/14-cryptographic-requirements.md)), persists it, and logs the operation ([§15](../part-5-reference/15-audit-observability.md)).

```
┌──────────┐      1. set_entry request       ┌───────────┐
│   Tool   │ ─────────────────────────────►  │ Guardian  │
└──────────┘                                 └───────────┘
                                                  │
                    2. Verify profile exists      │
                    3. Verify token auth (§9.3)   │
                    4. Evaluate write policy       │
                       (§10.2)                    │
                    5. Encrypt & persist (§14)    │
                    6. Log with audit context     │
                       (§15)                      │
                                                  │
                                             ┌────┴────┐
                                             │ Success │
                                             └────┬────┘
                                                  │
                    7. Return success        ◄────┘
                                                  │
┌──────────┐      8. Update local cache     ◄────┘
│   Tool   │◄───────────────────────────────
└──────────┘
```

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| WRITE-1 | MUST | Tool write requests MUST follow the write-through protocol: the tool sends the request to the Guardian, the Guardian verifies the token ([§9.3](09-access-control.md#93-token-verification)), evaluates the write approval policy ([§10.2](10-approval-policies.md#102-write-approval-modes)), encrypts the value ([§14](../part-5-reference/14-cryptographic-requirements.md)), persists the encrypted value, and logs the write with audit context ([§15](../part-5-reference/15-audit-observability.md)) |
| WRITE-2 | MUST | If any step in the write-through protocol fails, the tool's local cache (if present) MUST NOT be updated. The cache MUST reflect the last known-good state from the Guardian |
| WRITE-3 | MUST | Write operations MUST be atomic: either the value is persisted and the audit log entry is written, or neither occurs. Partial writes (value persisted without audit, or audit without persistence) are prohibited |
| WRITE-4 | MUST | Concurrent writes to the same entry MUST be serialized by the Guardian. The Guardian MUST NOT return success to a write request until persistence and audit logging are complete |
| WRITE-5 | MUST | The audit log entry for a write operation MUST include: token identity (partial `token_id`), profile name, entry key, write approval method (`auto`, `same`, `prompt_always`), and timestamp. Secret values MUST NOT appear in the audit log for entries with `sensitive=true` ([§15](../part-5-reference/15-audit-observability.md)) |
| WRITE-6 | MUST | Authorization failures and profile-resolution failures for write requests MUST return indistinguishable responses to unauthorized callers, consistent with [TOKEN-15](09-access-control.md#93-token-verification) |

### What This Prevents

- **[TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios):** Token scoping (WRITE-1 → [TOKEN-11](09-access-control.md#93-token-verification)) prevents a malicious tool from writing poisoned values to another tool's profile
- **[TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios):** Write approval policy evaluation (WRITE-1) ensures that malicious OAuth token substitution is subject to the profile's configured write policy. Profiles with static credentials use `deny` to eliminate the write vector entirely
- **[TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios):** Audit logging (WRITE-5) and write atomicity (WRITE-3) enable detection of progressive secret harvesting via write-back across sessions

## 11.3 Write Modes

Write modes are defined in [§4.5](../part-1-foundations/04-core-concepts.md#45-lifecycle-terms) and governed by the normative requirements in [§10.2](10-approval-policies.md#102-write-approval-modes) (APPR-6 through APPR-11). This section restates the modes for convenience. The authoritative definitions are in §4.5 and §10.2.

| Mode | Behavior | Governed By |
|------|----------|-------------|
| `same` | Evaluates writes using the profile's current read approval policy at the time of each write request ([APPR-7](10-approval-policies.md#102-write-approval-modes)) | [§10.2](10-approval-policies.md#102-write-approval-modes) |
| `auto` | Writes always allowed with valid token ([APPR-8](10-approval-policies.md#102-write-approval-modes)) | [§10.2](10-approval-policies.md#102-write-approval-modes) |
| `deny` | Writes unconditionally rejected -- profile is read-only from the tool's perspective ([APPR-9](10-approval-policies.md#102-write-approval-modes)) | [§10.2](10-approval-policies.md#102-write-approval-modes) |
| `prompt_always` | Every write requires human confirmation regardless of read policy or session state ([APPR-10](10-approval-policies.md#102-write-approval-modes)) | [§10.2](10-approval-policies.md#102-write-approval-modes) |

## 11.4 Guardian-Managed Refresh

When the Guardian can perform credential refresh directly -- without involving the tool -- the write attack surface is eliminated entirely. The tool requests a read; the Guardian detects the credential is expired or approaching expiry; a configured **refresh provider** obtains a fresh value; the Guardian persists, encrypts, and audit-logs the update internally; and the tool receives a valid credential. The tool never writes. The write policy is `deny`.

This is the preferred lifecycle model for standard credential types where the Guardian has sufficient information to perform the refresh: OAuth 2.0 token refresh, API key rotation via provider APIs, certificate renewal, and any credential type where the refresh operation requires only values the Guardian already holds (e.g., `refresh_token`, `client_secret`, `token_url`).

```
┌──────────┐      1. get_entry request       ┌───────────┐
│   Tool   │ ─────────────────────────────►  │ Guardian  │
└──────────┘                                 └───────────┘
                                                  │
                    2. Verify token auth (§9.3)   │
                    3. Evaluate read policy        │
                       (§10.1)                    │
                    4. Entry expired or            │
                       approaching expiry?        │
                       ┌──────────────────────┐   │
                       │ Yes:                 │   │
                       │  5. Invoke refresh   │   │
                       │     provider         │   │
                       │  6. Provider returns │   │
                       │     fresh value      │   │
                       │  7. Encrypt & persist│   │
                       │     (§14)            │   │
                       │  8. Log refresh      │   │
                       │     (§15)            │   │
                       └──────────────────────┘   │
                    9. Return fresh value     ◄────┘
                                                  │
┌──────────┐                                 ◄────┘
│   Tool   │◄───────────────────────────────
└──────────┘
   Tool only reads. Write policy is 'deny'.
   No write attack surface exists.
```

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| GREF-1 | MAY | Implementations MAY support Guardian-managed refresh through configurable refresh providers. At Level 2 and above, implementations SHOULD support at least one refresh provider type (e.g., OAuth 2.0 token refresh) |
| GREF-2 | MUST | Refresh providers MUST be configured by the human principal through the implementation's administrative interface. Tools and agents MUST NOT configure, modify, or select refresh providers |
| GREF-3 | MUST | When a refresh provider is configured for a profile, the Guardian MUST invoke it transparently when a tool requests an entry that the Guardian determines is expired or approaching expiry. The tool MUST NOT need to be aware that a refresh occurred -- the read request returns a valid value regardless of whether a refresh was performed |
| GREF-4 | MUST | The refresh operation MUST be atomic: either the refreshed value is encrypted, persisted, and audit-logged, or the previous value is returned unchanged. If the refresh provider fails, the Guardian MUST return the existing (potentially expired) value and log the refresh failure |
| GREF-5 | MUST | Refresh provider invocations MUST be audit-logged as a distinct event type, recording: profile name, entry key(s) refreshed, refresh provider type, success or failure, and timestamp. Refreshed secret values MUST NOT appear in the audit log for entries with `sensitive=true` ([§15](../part-5-reference/15-audit-observability.md)) |
| GREF-6 | MUST | Refresh providers MUST NOT have access to entries in other profiles. The provider operates within the scope of the single profile it is configured for, consistent with Boundary 2 ([§6.2](../part-2-principles/06-trust-boundaries.md#62-boundary-2-secret-scoping-tool-a--tool-b)) |
| GREF-7 | MUST | Refresh provider credentials (e.g., the `client_secret` and `refresh_token` used for OAuth) MUST be entries within the same profile, encrypted at rest and subject to the same cryptographic requirements as all other entries ([§14](../part-5-reference/14-cryptographic-requirements.md)) |
| GREF-8 | SHOULD | When Guardian-managed refresh is configured for a profile, the profile's write policy SHOULD be set to `deny` ([APPR-9](10-approval-policies.md#102-write-approval-modes)). If tool-initiated write-back is not operationally required, eliminating it removes the write attack surface ([TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios)) |
| GREF-9 | SHOULD | Implementations SHOULD support configurable expiry detection for refresh providers. Mechanisms include: an `expires_at` metadata field on the entry, a configurable time-before-expiry threshold for proactive refresh, and provider-specific expiry inference (e.g., decoding JWT `exp` claims). Example expiry detection mechanisms are provided in [Annex A](../annexes/annex-a-protocol-details.md) |
| GREF-10 | MUST | If a refresh provider requires outbound network access (e.g., contacting an OAuth token endpoint), the Guardian process MUST restrict outbound connectivity to only the endpoints required by configured providers. Implementations MUST NOT grant the Guardian blanket outbound network access |
| GREF-11 | MUST | Refresh provider failures MUST NOT block the read request indefinitely. Implementations MUST enforce a configurable timeout on refresh provider invocations (default: 30 seconds). If the timeout expires, the Guardian MUST return the existing value and log the timeout |
| GREF-12 | SHOULD | Implementations SHOULD support a refresh lock to prevent concurrent refresh attempts for the same entry. If a refresh is already in progress, subsequent read requests for the same entry SHOULD wait for the in-progress refresh to complete (up to the GREF-11 timeout) rather than initiating a parallel refresh |

### What This Prevents

- **[TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios) and [TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios) -- eliminated, not mitigated.** When write policy is `deny` (GREF-8) and all credential refresh is Guardian-managed, tools have no write path. A compromised tool cannot poison credentials for future invocations because it has no mechanism to write. This is a stronger security posture than tool-initiated write-back with audit logging -- the attack vector does not exist.
- **[TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios):** Progressive harvesting via write-back is impossible when tools cannot write. The Guardian's internal refresh operations are audited (GREF-5) but are not tool-initiated -- they are triggered by legitimate read requests and constrained to the profile's configured refresh provider.

### Refresh Provider Model

Refresh providers are an extension point. The standard defines the properties a refresh provider must satisfy; example provider types, registration mechanisms, and configuration schemas are provided in [Annex A](../annexes/annex-a-protocol-details.md).

**Properties all refresh providers MUST satisfy:**

| Property | Requirement |
|----------|-------------|
| Scoped to one profile | Provider can only access entries within its configured profile (GREF-6) |
| Configured by human principal | Only the human principal can register, modify, or remove providers (GREF-2) |
| Audited | Every invocation is audit-logged with outcome (GREF-5) |
| Fail-safe | Provider failure returns existing value, does not block reads (GREF-4, GREF-11) |
| Network-constrained | Outbound access limited to required endpoints (GREF-10) |

**Example provider types** (non-normative; see [Annex A](../annexes/annex-a-protocol-details.md) for details):

| Provider Type | Refresh Mechanism | Inputs from Profile |
|---------------|-------------------|---------------------|
| OAuth 2.0 | `grant_type=refresh_token` to `token_url` | `refresh_token`, `client_id`, `client_secret`, `token_url` |
| API key rotation | Provider-specific rotation API | Service-specific credentials, rotation endpoint |
| Certificate renewal | ACME or provider-specific renewal | Account key, domain, CA endpoint |
| Cloud credential | Cloud provider STS or IAM API | Role ARN, session parameters |

### When to Use Each Model

| Criterion | Guardian-Managed Refresh | Tool-Initiated Write-Back |
|-----------|--------------------------|---------------------------|
| Refresh logic is standard (OAuth 2.0, known API) | Preferred -- Guardian handles it | Not needed |
| Refresh requires tool-side state or context | Not applicable | Required |
| Refresh requires tool-specific auth flow | Not applicable | Required |
| Profile holds credentials the Guardian can use to refresh | Preferred | Not needed |
| Minimizing tool write permissions is a priority | Preferred -- write policy is `deny` | Write policy must permit writes |
| Guardian has outbound network access to the token endpoint | Preferred | Alternative when Guardian is network-constrained |
| Deployment is Level 1 (basic) | May not be available (GREF-1) | Available at all levels |

## 11.5 Sensitivity Preservation

When a tool writes a new value for an existing entry, the sensitivity classification of that entry must be preserved unless explicitly overridden. This separates the concern of "update the value" from "reclassify the entry" and prevents tools from accidentally -- or maliciously -- downgrading sensitivity during routine operations like token refresh. This applies equally to tool-initiated writes, Guardian-managed refresh, and initial provisioning (the Guardian preserves or sets sensitivity classifications in all cases).

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| SENS-1 | MUST | When a write request does not include a sensitivity flag, the Guardian MUST preserve the existing entry's sensitivity classification. The written value inherits the sensitivity of the entry it replaces. This applies to both tool-initiated writes and Guardian-managed refresh operations |
| SENS-2 | MUST | When a write request creates a new entry (the key does not exist in the profile) and does not include a sensitivity flag, the Guardian MUST default to `sensitive=true` (see [§5.3](../part-2-principles/05-design-principles.md#53-principle-of-declared-sensitivity)) |
| SENS-3 | MUST | To change an entry's sensitivity classification on write, the tool MUST include an explicit sensitivity flag in the write request. The Guardian MUST evaluate the profile's write approval policy before applying the sensitivity change |
| SENS-4 | SHOULD | Implementations SHOULD log sensitivity classification changes as a distinct audit event, recording the previous and new sensitivity values, to enable detection of unauthorized sensitivity downgrade attacks |

### What This Prevents

- **[TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios):** A compromised tool that can write back cannot silently downgrade an entry's sensitivity from `true` to `false` without explicit action (SENS-3) and audit visibility (SENS-4). Downgrading sensitivity would cause the entry to appear in audit logs and UI displays where it was previously masked -- a prerequisite for broader exfiltration.

> **Note:** The following illustrates conformant sensitivity preservation. The specific API is implementation-defined.
>
> ```python
> # Tool code doesn't need to know about sensitivity
> vault.set_entry("access_token", new_token)
> # Guardian preserves sensitivity=true from original entry (SENS-1)
>
> # Explicitly change sensitivity (evaluated against write policy, SENS-3)
> vault.set_entry("access_token", new_token, sensitive=False)
> ```

## 11.6 Delete Operations

Tools **MAY** delete individual entries through the Guardian. Delete is a destructive operation subject to write authorization and audit requirements.

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| DELETE-1 | MUST | Delete requests MUST follow the same token verification sequence as write operations ([§9.3](09-access-control.md#93-token-verification)) |
| DELETE-2 | MUST | Delete requests MUST be evaluated against the profile's write approval policy ([§10.2](10-approval-policies.md#102-write-approval-modes)). There is no separate delete policy |
| DELETE-3 | MUST | Delete operations MUST be atomic: either the entry is removed and the audit log entry is written, or neither occurs (consistent with WRITE-3) |
| DELETE-4 | MUST | The audit log entry for a delete operation MUST include: token identity (partial `token_id`), profile name, the entry key being deleted, the delete approval method, and timestamp ([§15](../part-5-reference/15-audit-observability.md)) |
| DELETE-5 | MUST | Tools MUST NOT delete profiles. Only individual entries within a profile may be deleted through the tool API. Profile deletion is a human principal administrative operation |
| DELETE-6 | MUST | If a deleted entry is referenced by an active `prompt_once` session's approved entry set ([SESS-6](10-approval-policies.md#103-session-approval-cache)), that entry MUST be removed from the approved set. Subsequent requests for the deleted entry MUST return an error |
| DELETE-7 | SHOULD | Implementations SHOULD support a configurable retention period for deleted entries (soft-delete or tombstone) to support audit recovery and forensic analysis |
| DELETE-8 | SHOULD | Deletion of entries marked `sensitive=true` SHOULD require explicit human confirmation regardless of the profile's write mode, unless the profile operates at Tier 2 or Tier 3 with `auto` write policy ([§7.3](../part-2-principles/07-autonomy-tiers.md#73-tier-2-tool-autonomous), [§7.4](../part-2-principles/07-autonomy-tiers.md#74-tier-3-full-delegation)) |

### What This Prevents

- **[TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios):** Token scoping (DELETE-1) prevents a compromised tool from deleting entries in profiles it isn't authorized to access
- **Denial-of-service via deletion:** A compromised tool with write access could delete critical entries, causing cascading failures for all tools that depend on those entries. DELETE-7 (soft-delete / tombstone) enables recovery. DELETE-8 adds a human gate for high-sensitivity entries

### Use Cases

Delete operations should be used sparingly. Most secret lifecycle operations are updates, not deletions:

- Removing deprecated entries during migration
- Cleaning up test entries
- Removing credentials that are no longer needed

## 11.7 Write Failure Handling

When a write operation fails, the tool **MUST** handle the failure without exposing secrets or corrupting local state. This section specifies the required failure behaviors that operationalize the Principle of Degradation Toward Safety ([§5.5](../part-2-principles/05-design-principles.md#55-principle-of-degradation-toward-safety)).

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| WFAIL-1 | MUST | When the Guardian denies a write request (write policy is `deny`, or interactive approval is denied), the tool MUST NOT retry the write for the same entry within the same session. The tool MAY continue operating with the existing cached value |
| WFAIL-2 | MUST | When a write approval request times out (no human response within the configured timeout), the tool MUST treat the request as denied (see [DLG-8](../part-2-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)) |
| WFAIL-3 | MUST | When the Guardian is unavailable, the tool MUST NOT update its local cache and MUST NOT fall back to alternative write mechanisms (see [§5.5](../part-2-principles/05-design-principles.md#55-principle-of-degradation-toward-safety), Degradation Toward Safety) |
| WFAIL-4 | MUST | Write failures MUST NOT expose the value that was being written. Error responses from the Guardian MUST NOT include the submitted value |
| WFAIL-5 | SHOULD | Tools SHOULD log write failures at the tool level for operational diagnostics. Write failure logs MUST NOT include secret values |

> **Note:** The following illustrates conformant failure handling. The specific API and exception types are implementation-defined.
>
> ```python
> try:
>     vault.set_entry("access_token", new_token)
> except WriteDeniedError:
>     # Write policy is 'deny' -- continue with existing token (WFAIL-1)
>     log.warning("Cannot persist refreshed token, using existing")
> except ApprovalTimeoutError:
>     # Approval required but timed out -- treat as denied (WFAIL-2)
>     log.error("Token refresh not approved, stopping")
>     raise
> except GuardianUnavailableError:
>     # Guardian unreachable -- do not update local cache (WFAIL-3)
>     log.error("Guardian unavailable, cannot persist token")
>     raise
> ```

## 11.8 Lifecycle Patterns

> **Note:** The guidance in this section is non-normative. It illustrates common lifecycle configurations using the provisioning models defined in [§11.1](#111-secret-provisioning), the approval modes defined in [§10.1](10-approval-policies.md#101-read-approval-modes), [§10.2](10-approval-policies.md#102-write-approval-modes), the autonomy tiers defined in [§7](../part-2-principles/07-autonomy-tiers.md), and Guardian-managed refresh ([§11.4](#114-guardian-managed-refresh)). The human principal selects the configuration appropriate to each profile's risk posture.

### Static API Key

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Human-seeded (manual entry) | [PROV-1](#111-secret-provisioning) |
| Read policy | `prompt_once` | [APPR-3](10-approval-policies.md#101-read-approval-modes), [§7.2 Tier 1](../part-2-principles/07-autonomy-tiers.md#72-tier-1-session-trusted) |
| Write policy | `deny` | [APPR-9](10-approval-policies.md#102-write-approval-modes) |
| Refresh provider | None | -- |
| Rotation | Manual (human principal creates new profile) | -- |

Use case: Third-party API key that never changes. If rotation is needed, create a new profile and update tool configuration.

### OAuth Client (Guardian-Managed)

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Guardian-mediated (OAuth authorization code flow) | [PROV-5](#111-secret-provisioning) |
| Read policy | `prompt_once` | [APPR-3](10-approval-policies.md#101-read-approval-modes), [§7.2 Tier 1](../part-2-principles/07-autonomy-tiers.md#72-tier-1-session-trusted) |
| Write policy | `deny` | [APPR-9](10-approval-policies.md#102-write-approval-modes), [GREF-8](#114-guardian-managed-refresh) |
| Refresh provider | OAuth 2.0 (`refresh_token` grant) | [GREF-1](#114-guardian-managed-refresh) |
| Rotation | Automatic (Guardian refreshes transparently) | [GREF-3](#114-guardian-managed-refresh) |

Use case: Full Guardian-managed lifecycle. The Guardian orchestrates the initial OAuth authorization code exchange (PROV-5), populates the profile, configures the refresh provider (PROV-9), and handles all subsequent token refreshes transparently. Tool never writes -- not on day one, not on day 100. Write attack surface does not exist.

### OAuth Client (Tool-Initiated)

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Human-seeded (human obtains tokens externally and enters them) | [PROV-1](#111-secret-provisioning) |
| Read policy | `prompt_once` | [APPR-3](10-approval-policies.md#101-read-approval-modes), [§7.2 Tier 1](../part-2-principles/07-autonomy-tiers.md#72-tier-1-session-trusted) |
| Write policy | `auto` | [APPR-8](10-approval-policies.md#102-write-approval-modes) |
| Refresh provider | None | -- |
| Rotation | Automatic (tool refreshes `access_token` via write-back) | WRITE-1 |

Use case: OAuth credentials where the tool handles refresh (custom grant types, tool-specific auth flows, or deployments where the Guardian lacks outbound network access to the token endpoint). Tool requires write access.

### Rotating Secret

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Human-seeded (manual entry) | [PROV-1](#111-secret-provisioning) |
| Read policy | `prompt_always` | [APPR-4](10-approval-policies.md#101-read-approval-modes), [§7.1 Tier 0](../part-2-principles/07-autonomy-tiers.md#71-tier-0-supervised) |
| Write policy | `prompt_always` | [APPR-10](10-approval-policies.md#102-write-approval-modes) |
| Refresh provider | None | -- |
| Rotation | Manual with human approval on every access and modification | -- |

Use case: High-security credentials where every access and modification requires human awareness.

### Environment Config

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Human-seeded or programmatic | [PROV-1](#111-secret-provisioning), [PROV-12](#111-secret-provisioning) |
| Read policy | `auto` | [APPR-2](10-approval-policies.md#101-read-approval-modes), [§7.3 Tier 2](../part-2-principles/07-autonomy-tiers.md#73-tier-2-tool-autonomous) |
| Write policy | `deny` | [APPR-9](10-approval-policies.md#102-write-approval-modes) |
| Refresh provider | None | -- |
| Rotation | N/A (non-secret configuration) | -- |

Use case: Non-secret configuration (endpoints, regions, feature flags) stored alongside secrets for operational convenience.

### Session Token

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Programmatic (CI/CD or orchestration system) | [PROV-12](#111-secret-provisioning) |
| Read policy | `auto` | [APPR-2](10-approval-policies.md#101-read-approval-modes), [§7.3 Tier 2](../part-2-principles/07-autonomy-tiers.md#73-tier-2-tool-autonomous) |
| Write policy | `auto` | [APPR-8](10-approval-policies.md#102-write-approval-modes) |
| Refresh provider | None | -- |
| Rotation | Automatic (tool-initiated) | -- |

Use case: Short-lived tokens in trusted environments where both read and write are automated.

### Cloud Credential (Guardian-Managed)

| Setting | Value | Cross-Reference |
|---------|-------|-----------------|
| Provisioning | Programmatic (infrastructure automation seeds role credential) | [PROV-12](#111-secret-provisioning) |
| Read policy | `prompt_once` | [APPR-3](10-approval-policies.md#101-read-approval-modes), [§7.2 Tier 1](../part-2-principles/07-autonomy-tiers.md#72-tier-1-session-trusted) |
| Write policy | `deny` | [APPR-9](10-approval-policies.md#102-write-approval-modes), [GREF-8](#114-guardian-managed-refresh) |
| Refresh provider | Cloud STS (e.g., AWS STS `AssumeRole`) | [GREF-1](#114-guardian-managed-refresh) |
| Rotation | Automatic (Guardian obtains fresh session credentials) | [GREF-3](#114-guardian-managed-refresh) |

Use case: Cloud provider credentials where infrastructure automation provisions the long-lived role credential (PROV-12), and the Guardian obtains short-lived session tokens on demand. Tools receive fresh session credentials on every read without write access.

## 11.9 OAuth Token Refresh Flows

> **Note:** The following end-to-end walkthroughs are non-normative. They illustrate how the normative requirements in this section, [§9](09-access-control.md), [§10](10-approval-policies.md), and [§15](../part-5-reference/15-audit-observability.md) compose to support the most common write-back scenario under both lifecycle models. Specific method names, audit log formatting, and protocol details are provided in [Annex A](../annexes/annex-a-protocol-details.md).

### Guardian-Managed Refresh (Preferred)

```
1. Tool requests read: access_token
   Guardian: Verifies token (TOKEN-10), evaluates read policy (APPR-3).
            Prompt_once -- presents approval dialog.
            Human approves. Session cached (SESS-6).

2. Guardian detects access_token is expired (GREF-9).
   Guardian: Invokes configured OAuth 2.0 refresh provider (GREF-3).
            Provider uses refresh_token + client_secret from same profile (GREF-7).
            Provider contacts token_url, receives new access_token.
   Guardian: Encrypts and persists new access_token (§14).
            Preserves sensitivity=true (SENS-1).
   Audit:   Guardian-managed refresh logged (GREF-5).

3. Guardian returns fresh access_token to tool.
   Tool calls external API -- success.

The tool never wrote. Write policy is 'deny'.
The agent never saw any secret value.
TS-5 and TS-10 do not apply -- no write path exists.
```

### Tool-Initiated Write-Back (Fallback)

```
1. Tool requests read: access_token, refresh_token, token_url
   Guardian: Verifies token (TOKEN-10), evaluates read policy (APPR-3).
            Prompt_once -- presents approval dialog.
            Human approves. Session cached (SESS-6).
   Guardian: Returns requested entries.
   Audit:   Read access logged (§15).

2. Tool calls external API with access_token.
   API returns 401 Unauthorized.

3. Tool requests read: refresh_token
   Guardian: Session already approved for this entry (SESS-6).
            Returns refresh_token without re-prompting.
   Audit:   Session-cached read logged (§15).

4. Tool performs OAuth token refresh with refresh_token.
   OAuth server returns new access_token.

5. Tool requests write: access_token = new_access_token
   Guardian: Verifies token (TOKEN-10).
            Write policy is 'auto' (APPR-8) -- approved.
            Encrypts value (§14). Persists. Logs write (WRITE-5).
            Preserves sensitivity=true (SENS-1).
   Audit:   Write operation logged with approval method (§15).

6. Tool retries external API with new_access_token.
   API returns success.

The agent never saw any secret value at any step.
The Guardian mediated every read and write.
Every operation is recorded in the audit log.
```

---

Next: [Delegation](12-delegation.md)
