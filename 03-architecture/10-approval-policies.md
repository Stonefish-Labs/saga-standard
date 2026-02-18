# 10. Approval Policies and Human Oversight

Approval policies govern how secret access is authorized at runtime. They are the primary mechanism by which this standard implements human oversight, operationalizing the Principle of Human Supremacy ([§5.6](../02-principles/05-design-principles.md#56-principle-of-human-supremacy)) and enforcing Boundary 3 of the trust model ([§6.3](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)).

Approval policies are configured per-profile ([§8](08-secret-profiles.md), PROFILE-3, PROFILE-4). The read approval modes (`auto`, `prompt_once`, `prompt_always`) are defined in [§4.4](../01-foundations/04-core-concepts.md#44-approval-terms). The write modes (`same`, `auto`, `deny`, `prompt_always`) are defined in [§4.5](../01-foundations/04-core-concepts.md#45-lifecycle-terms). The autonomy tiers ([§7](../02-principles/07-autonomy-tiers.md)) map specific approval and write mode combinations to named operational postures.

## 10.1 Read Approval Modes

Every profile **MUST** have an associated read approval policy set to one of: `auto`, `prompt_once`, or `prompt_always`.

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| APPR-1 | MUST | Every profile MUST have a read approval policy set to one of: `auto`, `prompt_once`, or `prompt_always` |
| APPR-2 | MUST | `auto` mode: The Guardian MUST grant access to the requested entries if the token is valid, without interactive approval. No human notification is required at the time of access. The policy is set at the profile level, but approval (or its absence) is evaluated per entry request |
| APPR-3 | MUST | `prompt_once` mode: The Guardian MUST prompt the human principal to approve access on first request. Upon approval, the Guardian MUST cache the approval for the specific entries shown in the approval dialog, for the configured session TTL ([§10.3](#103-session-approval-cache)). Subsequent requests for the same entries within the session MUST proceed without re-prompting. Requests for entries not in the approved set MUST trigger a new approval prompt (see SESS-7). **Entry-set snapshot:** The Guardian MUST snapshot the set of approved entries (entry keys and a hash of each entry's value) at dialog render time. Approval binds to that snapshot. If any approved entry's value changes between dialog render and human approval, the Guardian MUST discard the pending approval and re-prompt before serving the changed value under a session approval |
| APPR-4 | MUST | `prompt_always` mode: The Guardian MUST prompt the human principal for every access request. Session caching MUST NOT be used |
| APPR-5 | SHOULD | The default read approval policy for new profiles SHOULD be `prompt_once` (see [§7.2 Tier 1](../02-principles/07-autonomy-tiers.md)) |

> **`prompt_once` is the RECOMMENDED default for most profiles.** It preserves explicit human consent at session boundaries (addressing [TS-16](../01-foundations/03-threat-model.md#352-approval-social-engineering-ts-16)) while reducing friction for interactive workflows. See [§7.2 Tier 1](../02-principles/07-autonomy-tiers.md) for the tier-level rationale.

### Operational Characteristics

| Mode | Human Involvement | Friction | Risk |
|------|-------------------|----------|------|
| `auto` | None at access time | Lowest | Any tool with a valid token can access individual entries in the profile without human awareness. No human approval is required per entry |
| `prompt_once` | Once per entry set | Moderate | After initial approval, tools can access the approved entries until the session expires. Requests for additional entries require new approval |
| `prompt_always` | Every access | Highest | High friction; not suitable for high-frequency operations |

## 10.2 Write Approval Modes

Secret writes follow a separate, independently configured policy. The write modes are defined in [§4.5](../01-foundations/04-core-concepts.md#45-lifecycle-terms).

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| APPR-6 | MUST | Every profile MUST have a write approval policy set to one of: `same`, `auto`, `deny`, or `prompt_always` |
| APPR-7 | MUST | `same` mode: The Guardian MUST evaluate write requests using the profile's current read approval policy at the time of each write request. Changes to the read approval policy automatically apply to writes when write mode is `same` |
| APPR-8 | MUST | `auto` mode: The Guardian MUST allow writes to the requested entries if the token is valid, without interactive approval |
| APPR-9 | MUST | `deny` mode: The Guardian MUST unconditionally reject all write requests. The profile is read-only from the tool's perspective |
| APPR-10 | MUST | `prompt_always` mode: The Guardian MUST prompt the human principal for every write request, regardless of read policy or session state |
| APPR-11 | SHOULD | The default write policy for new profiles SHOULD be `same` |

### What This Prevents

| Threat | Approval Mechanism | How It Helps |
|--------|-------------------|--------------|
| [TS-3](../01-foundations/03-threat-model.md#32-threat-scenarios): Prompt injection causes agent to access unintended entries | `prompt_once`, `prompt_always` modes | Human must explicitly approve access to each requested entry, regardless of what the agent was instructed to do. `auto` mode does not mitigate TS-3; it relies entirely on token scoping ([§9](09-access-control.md)) |
| [TS-9](../01-foundations/03-threat-model.md#32-threat-scenarios): Malicious process displays fake approval dialog | DLG-7 (agent can't dismiss), DLG-11 (Guardian-authoritative content), verification codes | The approval dialog cannot be forged by the agent or a malicious process. See [§6.3](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian) for the full Boundary 3 analysis |
| [TS-16](../01-foundations/03-threat-model.md#352-approval-social-engineering-ts-16): Social engineering via deceptive context | DLG-4 (complete entry list), DLG-11 (no agent text), DLG-12 (sensitivity display) | The human sees Guardian-authoritative information, not agent-curated context. The complete entry list and sensitivity labels prevent scope-hiding attacks |
| [TS-17](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17): Approval fatigue exploitation | Session caching (SESS-*), rate limiting ([§3.5.3](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17)) | `prompt_once` reduces prompt volume. Approval fatigue controls (Level 3, [§13.4](../04-conformance/13-conformance.md#134-level-3-advanced)) provide rate limiting and escalating scrutiny |

## 10.3 Session Approval Cache

When `prompt_once` is the approval mode, approved sessions are cached in Guardian memory.

### Session Cache Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| SESS-1 | MUST | Sessions MUST have a finite TTL |
| SESS-2 | MUST | Default TTL MUST NOT exceed 3600 seconds (1 hour) |
| SESS-3 | SHOULD | TTL SHOULD be configurable per profile |
| SESS-4 | MUST | Session cache MUST be invalidated on Guardian restart |
| SESS-5 | MUST | Session cache MUST be invalidated on token revocation |
| SESS-6 | MUST | Session cache MUST track the set of approved entries per profile and token. Only entries shown in the approval dialog and approved by the human principal are included in the approved set |
| SESS-7 | MUST | When a request includes entries not covered by an active session's approved set, the Guardian MUST present a new approval dialog showing only the entries requiring new approval (see DLG-14). Entries already in the approved set MUST NOT be re-prompted |
| SESS-8 | MUST | Upon approval of new entries, the session's approved entry set MUST be expanded to include the newly approved entries. The original session TTL MUST NOT be reset by entry expansion |

Session caches are held in Guardian memory only and **MUST NOT** be persisted to disk (see [§4.4 Session](../01-foundations/04-core-concepts.md#44-approval-terms)). Guardian restart clears all session caches, requiring re-approval for all `prompt_once` profiles.

### Session Cache Security

| Property | Requirement |
|----------|-------------|
| Storage | In-memory only. Disk persistence is prohibited ([§4.4](../01-foundations/04-core-concepts.md#44-approval-terms)) |
| Isolation | Session cache MUST be scoped to the approved profile, token, and specific approved entries |
| Invalidation | Sessions MUST be invalidated on Guardian restart, token revocation, TTL expiry, or explicit human revocation, whichever occurs first |
| Key rotation | Sessions MUST be invalidated on master key rotation (see [Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md)) |
| Integrity | The session cache data structure MUST include an HMAC over each session entry's contents (profile name, token identity, approved entry set, TTL, creation timestamp), computed using the session integrity key (SKEY-1 through SKEY-5, below). If a session cache entry fails HMAC verification on read, the entry MUST be invalidated immediately and a WARN-level audit event MUST be generated. This requirement protects against memory corruption attacks that could forge session approval state |

### Session Integrity Key Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| SKEY-1 | MUST | The session integrity key **MUST** be generated at Guardian startup using a CSPRNG (KEY-3). It **MUST** be at least 256 bits (32 bytes) |
| SKEY-2 | MUST | The session integrity key **MUST** be held in Guardian process memory only. It **MUST NOT** be written to disk, persisted to any storage, logged, or transmitted |
| SKEY-3 | MUST | The session integrity key **MUST** be entirely distinct from the master encryption key and from the delegation signing key. It **MUST** be independently generated; derivation from the master key (e.g., via HKDF) is **NOT** permitted |
| SKEY-4 | MUST | The session integrity key **MUST** be destroyed (memory overwritten) when the Guardian process shuts down. Because the key is not persisted, it cannot be recovered after restart; this is by design — Guardian restart invalidates all session cache entries (SESS-4) |
| SKEY-5 | MUST | If the session integrity key is lost or becomes unavailable for any reason, the Guardian **MUST** treat all existing session cache entries as invalid (fail-closed). A new key **MUST** be generated before resuming operation. The key loss **MUST** be logged at WARN level |

## 10.3a Sensitivity Classification Change Logging

The operational requirement for sensitivity classification change logging is specified normatively as **SENS-4** in [§11.5](../03-architecture/11-secret-lifecycle.md#115-sensitivity-preservation). That requirement is authoritative and covers both sensitivity upgrades (`sensitive=false` → `sensitive=true`) and downgrades (`sensitive=true` → `sensitive=false`). Implementations consulting this section for operational behavior **MUST** refer to §11.5 SENS-4 as the canonical requirement.

## 10.4 Approval Channel Requirements

The normative approval channel requirements are specified in [§6.3 Boundary 3: Approval Attestation](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian) as **DLG-1 through DLG-15**. Implementations **MUST** conform to those definitions. §6.3 is the sole authoritative source for DLG-* requirements; this section does not restate them.

> **Why this section does not restate DLG requirements:** Prior revisions maintained a local copy of the DLG-* requirements in this section. That copy produced normative drift (DLG-6 was listed as SHOULD here while §6.3 says MUST; DLG-6a was absent entirely). Maintaining non-authoritative copies of normative requirements is a standards anti-pattern. Implementers and conformance reviewers **MUST** consult §6.3 directly for DLG-* requirements.

**Key DLG properties for implementers consulting this section:**

| Property | Where specified |
|----------|----------------|
| Channel independence (agent cannot intercept/forge/dismiss) | DLG-1 (§6.3) |
| Complete entry display without truncation | DLG-4 (§6.3) |
| Verification code delivery channel requirements | DLG-6, DLG-6a (§6.3) |
| Guardian-authoritative dialog content only | DLG-11 (§6.3) |
| Agent process capability test for single-machine deployments | DLG-15 (§6.3) |

### Example Dialog

> **Note:** The following example illustrates a conformant approval dialog. The specific layout and visual presentation are implementation-defined; conformance is determined by the DLG-* requirements above.

```
┌─────────────────────────────────────────────────┐
│  Secret Access Request                          │
│                                                 │
│  Profile: aws-production                        │
│  Token:   deploy-bot (a1b2c3d4)                 │
│  Policy:  prompt_once                           │
│                                                 │
│  Entries requested (1 of 3 sensitive):          │
│    access_key_id                                │
│    secret_access_key    🔒 sensitive             │
│    region                                       │
│                                                 │
│  Verification Code: XKCD-7291                   │
│                                                 │
│  ⚠ All dialog content is Guardian-              │
│    authoritative. Verify this matches           │
│    your intended operation.                     │
│                                                 │
│  [ Deny ]                        [ Approve ]    │
└─────────────────────────────────────────────────┘
```

### Verification Code Flow

When verification codes are implemented (see DLG-5), the following flow provides anti-spoofing assurance:

```
1. Tool requests access to profile
2. Guardian generates verification code
3. Guardian displays code in approval dialog
4. Guardian makes the verification code available to the tool through the protocol response
5. Tool displays code in its output
6. User verifies codes match
7. User clicks Approve or Deny
```

Verification code format requirements are defined in [§4.4 Approval Integrity](../01-foundations/04-core-concepts.md#44-approval-terms). Example delivery mechanisms are provided in [Annex A](../07-annexes/annex-a-protocol-details.md). See [§6.3](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian) for the full Boundary 3 analysis including relay attack considerations.

## 10.5 Headless Operation

Some deployments (CI/CD, servers, containers) cannot display interactive dialogs.

### Headless Mode Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| HEAD-1 | MUST | Headless mode MUST be explicitly opted into |
| HEAD-2 | MUST | When no alternative approval channel is configured (see [§10.6](#106-webhook-based-approval)), only `auto` approval profiles are accessible in headless mode |
| HEAD-3 | MUST | When no alternative approval channel is configured, `prompt_once` or `prompt_always` profiles MUST be denied in headless mode |
| HEAD-4 | SHOULD | Headless mode SHOULD be logged distinctly from interactive mode |
| HEAD-5 | MAY | Implementations MAY support webhook-based or out-of-band approval channels for headless environments (see [§10.6](#106-webhook-based-approval)). When such a channel is configured and operational, profiles requiring interactive approval MAY be accessed through the alternative channel |

### Headless Detection

Headless mode is enabled through an implementation-defined mechanism (environment variable, configuration file, or startup flag). Explicit configuration is preferred over auto-detection to prevent accidental headless operation.

## 10.6 Webhook-Based Approval

For headless environments that still need interactive approval, implementations **MAY** support webhook-based approval as an alternative approval channel. When webhook-based approval is configured and operational, it serves as the interactive approval mechanism for `prompt_once` and `prompt_always` profiles that would otherwise be denied in headless mode (see HEAD-2, HEAD-3, HEAD-5).

### Webhook Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| WHOOK-1 | MUST | Webhook URL MUST be explicitly configured |
| WHOOK-2 | MUST | Payload MUST include profile name, token name, partial token ID, entry keys being requested, and verification code (when implemented) |
| WHOOK-3 | MUST | Webhook delivery MUST be asynchronous; the Guardian MUST NOT block on the HTTP response from the webhook endpoint. The Guardian waits for the approval callback (if applicable) subject to the WHOOK-8 timeout |
| WHOOK-4 | MUST | When webhook-based approval is used as the approval channel for `prompt_once` or `prompt_always` profiles, the webhook payload MUST include a callback URL for approval/denial responses. For notification-only webhooks (e.g., alerting on `auto` profile access), callback URLs are MAY |
| WHOOK-5 | MUST | Payload MUST NOT include secret values |
| WHOOK-6 | MUST | Webhook connections MUST use TLS. Plaintext HTTP webhook delivery is prohibited. Implementations MAY exempt localhost webhook URLs from the TLS requirement |
| WHOOK-7 | MUST | Webhook-based approval MUST have a configurable timeout (default: 300 seconds). If no approval response is received within the timeout, the request MUST be denied |
| WHOOK-8 | MUST | Webhook delivery failures MUST be logged and the access request MUST be denied with a diagnostic error. Failure diagnostics are internal only; error responses to the requesting tool MUST be indistinguishable from approval denial (see [TOKEN-15](09-access-control.md)) |
| WHOOK-9 | MUST | Callback path tokens (the token embedded in the callback URL path) MUST be generated by a CSPRNG with at least 128 bits of entropy. Each callback path token MUST be single-use: the Guardian MUST invalidate it immediately upon receiving a callback response (approve or deny) or upon WHOOK-7 timeout expiry, whichever occurs first. The Guardian MUST NOT accept a second POST to a previously-used or expired callback URL; such requests MUST be rejected with an HTTP 404 response and logged at WARN level. The webhook payload example using `abc123` as a callback URL path token is illustrative only; production implementations MUST generate tokens per this requirement |
| WHOOK-10 | MUST | Before sending a webhook to a configured URL, the Guardian MUST validate the target URL against SSRF mitigations. Resolved IP addresses for the webhook hostname MUST NOT be loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`), or private RFC 1918 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) or RFC 4193 ranges (`fc00::/7`). Exceptions are permitted only for explicitly allowlisted internal endpoints configured by the human principal and documented in the conformance statement. DNS rebinding protection MUST be applied: the IP address MUST be validated after DNS resolution and MUST be re-validated if DNS TTL expires before the webhook is delivered |

### Webhook Payload Example

> **Note:** The following example illustrates a conformant webhook payload. The specific field names and structure are provided in [Annex A](../07-annexes/annex-a-protocol-details.md).

```json
{
  "event": "approval_required",
  "profile": "production-db",
  "token_name": "deploy-bot",
  "token_id": "a1b2c3d4",
  "entries": ["db_host", "db_user", "db_password"],
  "verification_code": "ABCD-1234",
  "timestamp": "2026-02-16T12:00:00Z",
  "callback_url": "https://guardian.internal/approval/abc123"
}
```

### Integration Pattern

```
1. Tool requests access (prompt_once or prompt_always profile in headless)
2. Guardian sends webhook to configured endpoint (e.g., Slack, PagerDuty, custom service)
3. Notification includes profile, entries, and verification code
4. Human reviews and clicks Approve/Deny in notification
5. Notification service calls Guardian callback URL
6. Guardian grants or denies access
7. Tool receives response
```

If the callback is not received within the configured timeout (WHOOK-7), the Guardian denies the request.

## 10.7 Policy Configuration

Approval policies are set per-profile through the implementation's administrative interface. The profile attributes that store policy configuration are defined in [§8.1](08-secret-profiles.md) (PROFILE-3 for read approval policy, PROFILE-4 for write approval policy).

> **Note:** The guidance in this section is non-normative. It illustrates the policy attributes and their interactions but does not define conformance requirements beyond those specified in §10.1 through §10.6.

A complete policy configuration specifies:

| Attribute | Values | Default | Cross-Reference |
|-----------|--------|---------|-----------------|
| Read approval | `auto`, `prompt_once`, `prompt_always` | `prompt_once` (APPR-5) | [§4.4](../01-foundations/04-core-concepts.md#44-approval-terms) |
| Write approval | `same`, `auto`, `deny`, `prompt_always` | `same` (APPR-11) | [§4.5](../01-foundations/04-core-concepts.md#45-lifecycle-terms) |
| Session TTL | Seconds (when read approval is `prompt_once`) | ≤ 3600 (SESS-2) | [§7 Tier 1](../02-principles/07-autonomy-tiers.md) (TIER-1-4) |

---

Next: [Secret Lifecycle](11-secret-lifecycle.md)
