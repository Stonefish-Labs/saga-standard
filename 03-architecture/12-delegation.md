# 12. Delegation and Cross-System Propagation

Multi-agent architectures introduce a cascading delegation problem: when Agent A delegates work to Agent B, secrets must flow through the chain without exposure, loss of audit trail, or privilege escalation. This section defines the normative requirements for secret delegation in multi-agent systems.

The delegation model addresses three threat scenarios from [§3.2](../01-foundations/03-threat-model.md#32-threat-scenarios):

- **[TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios)**: Cascading agent delegation causes unaudited access
- **[TS-13](../01-foundations/03-threat-model.md#32-threat-scenarios)**: Shared service retains credential beyond authorized scope
- **[TS-14](../01-foundations/03-threat-model.md#32-threat-scenarios)**: Shared service escalates credential to unauthorized resources

Delegation tokens are a **Level 3** capability (see [§13.4](../04-conformance/13-conformance.md#134-level-3-advanced)). Implementations at Level 1 and Level 2 are not required to support multi-agent delegation. Level 3 implementations **MUST** support the delegation requirements defined in this section.

The SAGA delegation model shares principles with established delegation mechanisms (OAuth 2.0 Token Exchange [RFC 8693], capability-based attenuation [Macaroons], identity delegation [SPIFFE]). SAGA differs in that delegation tokens are purely authorization artifacts (they never contain secret values) and the Guardian validates the full delegation chain on every request rather than relying on cryptographic capability chaining. See [§16 Relationship to Standards](../05-reference/16-relationship-to-standards.md).

## 12.1 The Delegation Problem

```
┌─────────────┐     delegates to     ┌─────────────┐     uses      ┌─────────────┐
│  Human      │ ──────────────────►  │  Agent A    │ ────────────► │  Tool A     │
│  Principal  │                      │             │               │             │
└─────────────┘                      └──────┬──────┘               └─────────────┘
                                            │
                                     delegates to
                                            │
                                            ▼
                                     ┌─────────────┐     uses      ┌─────────────┐
                                     │  Agent B    │ ────────────► │  Tool B     │
                                     │             │               │             │
                                     └─────────────┘               └─────────────┘
```

Agent B needs access to secrets that Agent A was authorized to use. But:

- Agent A cannot pass secret *values* to Agent B: this would violate process isolation ([Boundary 1](../02-principles/06-trust-boundaries.md))
- Agent B needs independent authorization from the Guardian
- The audit trail must show the full delegation chain from human principal to final tool

Delegation is an *authorization* problem, not a *secret distribution* problem. The delegation token carries the right to request secrets, never the secrets themselves.

> **Security note:** Delegation tokens are bearer credentials, subject to the same interception and replay risks as agent tokens ([TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios)). The mitigations are the same: short TTLs (DEL-12), single-use where possible (DEL-11), and transport encryption ([TOPO-1](../01-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)).

## 12.2 Delegation Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| DEL-1 | MUST | An agent **MUST NOT** pass secret values to another agent. Each agent **MUST** independently request secrets from the Guardian | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-2 | MUST | When Agent A delegates work to Agent B, Agent A **MUST** request a delegation token from the Guardian. The Guardian **MUST** create the delegation token, constrained to a subset of Agent A's authorized scope, and return it to Agent A for delivery to Agent B. Agent A **MUST NOT** create delegation tokens itself | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-14](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-3 | MUST | Delegation tokens **MUST NOT** contain secret values. A delegation token authorizes Agent B to request specific secrets from the Guardian; it does not carry or transmit those secrets | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-4 | MUST | Delegation tokens **MUST NOT** exceed the scope of the parent token. The set of accessible profiles, entries, and permissions in the delegation token **MUST** be a subset of, or equal to, those of the parent token | [TS-14](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-5 | MUST | Delegation tokens **MUST NOT** outlive the parent token. The expiration of a delegation token **MUST** be before or equal to the expiration of the parent token | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-6 | MUST | The Guardian **MUST** validate the full delegation chain, from the delegation token back to the originating human-principal-issued token, on every request. **Cross-request caching of chain validity is prohibited:** the Guardian **MUST NOT** reuse a previous chain validation result for a new incoming request; each new request triggers a fresh end-to-end chain walk. This ensures that mid-chain revocations (e.g., revocation of an intermediate parent token) are detected on the next request. Within-request caching (reusing chain validation results for multiple sub-operations within the same atomic request processing cycle) is permitted for performance, provided the revocation check is performed at the start of each new top-level request | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-7 | MUST | When a parent token is revoked or expires, all delegation tokens derived from it **MUST** be invalidated (cascade revocation). The Guardian **MUST** reject any new request received after the revocation timestamp for any delegation token in the cascade. In-flight operations that received a valid authorization decision before the revocation timestamp **MAY** complete, but **MUST** be logged at WARN level if they complete more than 30 seconds after the revocation timestamp. No grace period extends beyond 30 seconds from the revocation timestamp for any operation under a revoked delegation chain. The Guardian **MUST** record the cascade revocation event in the audit log, listing all invalidated delegation token IDs. See [§5.6 Human Supremacy](../02-principles/05-design-principles.md#56-principle-of-human-supremacy) | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-8 | MUST | Each agent in a delegation chain **MUST** appear as a distinct entity in the audit log. The audit entry for each delegated access **MUST** include: the delegation token ID, the parent token ID, the delegation chain depth, and the originating human principal. See [§15 Audit & Observability](../05-reference/15-audit-observability.md) | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-9 | MUST | At Level 3, implementations **MUST** enforce a configurable maximum delegation chain depth. The **RECOMMENDED** default maximum depth is 3. An unbounded chain depth enables O(n) I/O amplification attacks against the Guardian via DEL-6's per-request chain validation requirement and enables delegation chain depth attacks that consume Guardian resources proportionally to chain length. The maximum depth **MUST** be enforced atomically at delegation token creation time; the Guardian **MUST** reject requests to create delegation tokens that would exceed the configured maximum depth | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-9a | SHOULD/MUST | Implementations **SHOULD** enforce a configurable maximum number of concurrently active child delegation tokens per parent token (delegation breadth). The **RECOMMENDED** default breadth limit is 10 active child tokens per parent. An unbounded breadth limit enables resource exhaustion: an agent can issue an arbitrarily large number of child delegation tokens from a single parent token, requiring the Guardian to validate all of them on every request. The breadth limit **SHOULD** be enforced at delegation token creation time; the Guardian **SHOULD** reject requests to create delegation tokens from a parent that has already reached the breadth limit. **At Level 3, breadth enforcement is MUST** (see CONF-L3-2) | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-10 | MUST | Delegation tokens **MUST** be integrity-protected using a mechanism specified in [§14 Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md). The integrity key **MUST** be held exclusively by the Guardian and **MUST NOT** be shared with agents or tools | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-11 | MUST | When a delegation token specifies a maximum use count, the Guardian **MUST** enforce the count atomically: concurrent requests **MUST NOT** collectively exceed the configured maximum. When concurrent requests arrive simultaneously and would collectively exceed the use count, the Guardian **MUST** apply the following tie-breaking rule: grant requests in the order they are serialized at the storage layer (first-received, first-granted); requests that arrive when the use count is already exhausted **MUST** be rejected with a "use count exhausted" error indicating the token has been fully consumed — they **MUST NOT** be silently dropped, queued indefinitely, or granted a partial result. The Guardian **MUST** audit-log each use-count decrement, including the request that consumed the final use. **Multi-instance enforcement:** In deployments with multiple concurrent Guardian instances sharing a common vault backend, use-count enforcement MUST be implemented using a single-writer serialization mechanism at the storage layer; optimistic concurrency without storage-layer atomicity is **NOT** conformant because two concurrent Guardian instances can each independently read `current_uses < max_uses` and both proceed, resulting in over-issuance. Acceptable mechanisms include: (a) **database compare-and-swap (CAS)** — the Guardian atomically increments the use count only when the pre-read count matches the current stored value (e.g., `UPDATE ... SET use_count = use_count + 1 WHERE token_id = ? AND use_count < max_uses` with a row-level lock); (b) **distributed mutex** — a distributed lock (e.g., Redis SETNX, ZooKeeper ephemeral node, etcd lease) prevents concurrent use-count updates from separate Guardian instances; (c) **primary serialization** — all use-count updates are routed through a designated primary Guardian instance that holds an exclusive write lock on the token record. The conformance statement MUST document the specific use-count enforcement mechanism and confirm it is atomic across all Guardian instances in the deployment | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-12 | SHOULD | Delegation token TTLs **SHOULD NOT** exceed 3600 seconds (1 hour). TTLs exceeding one calendar day are **NOT RECOMMENDED**. Shorter TTLs limit the exposure window if a delegation token is intercepted ([TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios)) | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |

| DEL-20 (all levels) | MUST | **Confused deputy protection — applies at all conformance levels when delegation token creation is supported:** When a delegation token is created that grants access to a profile containing any entry with `sensitive=true`, the Guardian **MUST** present an interactive approval dialog to the human principal before issuing the token. This requirement applies regardless of the profile's read approval policy, **MUST NOT** be waived by the requesting agent, and **MUST NOT** be bypassed by development mode (see CONF-DEV-1). The approval dialog **MUST** identify: (a) the profile name, (b) all sensitive entries the delegation token will cover, (c) the scope of delegated permissions, and (d) the delegation chain depth at which the token will operate. The Guardian **MUST** record in the audit log the context in which the delegation token was created, including the originating request context if available. This requirement is in addition to any other approval requirements that apply to the profile. Additionally, implementations **SHOULD** configure `prompt_always` write policy on sensitive profiles to ensure each write operation through a delegation chain independently receives explicit human authorization, complementing this requirement which applies only at delegation token creation time |

> **Design rationale:** The delegation chain provides cryptographic integrity over scope and permissions, but cannot verify the human principal's intent at the moment an agent solicits the delegation. Prompt injection or social engineering by Agent A can cause the Guardian to issue a delegation token it should not have. DEL-20 ensures the human principal is in the loop at the highest-consequence moment — before a sensitive profile's access is delegated to another agent — not merely at the point when that agent uses it.

## 12.3 Delegation Token Properties

A delegation token **MUST** have the following properties. The concrete token structure (field names, encoding, and serialization format) is provided in [Annex A](../07-annexes/annex-a-protocol-details.md).

| ID | Level | Requirement |
|----|-------|-------------|
| DEL-13 | MUST | Each delegation token **MUST** have a unique identifier, generated from a cryptographically secure random source (see [§14 Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md)) |
| DEL-14 | MUST | Each delegation token **MUST** reference its parent token's identifier, enabling the Guardian to reconstruct the full delegation chain |
| DEL-15 | MUST | Each delegation token **MUST** specify the profile(s) and entry keys it authorizes. Wildcard entry scope (`*`) is **PROHIBITED** for profiles that contain any entry with `sensitive=true`; the Guardian **MUST** reject delegation token creation requests that specify wildcard scope for such profiles. For profiles containing only `sensitive=false` entries, wildcard scope is permitted but **NOT RECOMMENDED**; explicit entry enumeration **SHOULD** be preferred to enforce the [Principle of Minimal Disclosure](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure). When wildcard scope is used for a non-sensitive profile, this fact **MUST** be recorded in the delegation token creation audit entry |
| DEL-16 | MUST | Each delegation token **MUST** specify the permitted operations (`read`, `write`, `delete`). The permitted operations **MUST** be a subset of the parent token's permissions (DEL-4) |
| DEL-17 | MUST | Each delegation token **MUST** include an issuance timestamp and an expiration timestamp, both in UTC |
| DEL-18 | MAY | A delegation token **MAY** include a maximum use count. If present, the Guardian **MUST** enforce it atomically (DEL-11). A use count of 1 (single-use) is **RECOMMENDED** for one-time operations |
| DEL-19 | MUST | Each delegation token **MUST** include an integrity signature generated by the Guardian. The signature **MUST** cover all token fields. See [§14 Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md) for algorithm and key management |

> **Note:** An illustrative token structure with field names and a JSON example is provided in [Annex A](../07-annexes/annex-a-protocol-details.md). This standard defines the required properties; Annex A illustrates one conformant wire format.

## 12.4 Cross-System Delegation

Cross-system delegation builds on the remote Guardian deployment topology defined in [§3.6](../01-foundations/03-threat-model.md#36-guardian-deployment-topology). The TOPO-\* requirements (TOPO-1 through TOPO-8) apply to all remote Guardian deployments. The following requirements address delegation-specific concerns when agents on one system access secrets managed by a Guardian on a separate system.

| ID | Level | Requirement | Cross-Reference |
|----|-------|-------------|-----------------|
| CROSS-1 | MUST | Cross-system delegation requests **MUST** include the full delegation chain context, all token IDs from the delegation token back to the originating principal-issued token, to enable end-to-end audit reconstruction | DEL-8, [§15 Audit & Observability](../05-reference/15-audit-observability.md) |
| CROSS-2 | MUST | Each system in a cross-system delegation **MUST** maintain its own audit log recording all delegation requests and their outcomes | [§15 Audit & Observability](../05-reference/15-audit-observability.md) |
| CROSS-3 | MUST | Secrets obtained via cross-system delegation **MUST NOT** be cached or persisted on intermediate systems | [TOPO-6](../01-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment) |
| CROSS-4 | MUST | Cross-system credential federation **MUST** use one of the three mechanisms defined in [§14.5.2](../05-reference/14-cryptographic-requirements.md#1452-cross-system-signing-requirements) when delegation tokens cross independent trust domains (Guardian instances with separate master key hierarchies). Within the same trust domain (Guardian instances that share a pre-established mutual authentication channel registered per CROSS-5a, and are under common administrative control with a shared key distribution infrastructure), HMAC-signed tokens per Option C of §14.5.2 are permitted. The determination of "same trust domain" is based on security properties — shared administrative authority, pre-established key channel, and CROSS-5a registration — not on organizational or legal structure, which is not a security-verifiable property. HMAC-signed tokens from an unregistered Guardian instance **MUST** be rejected | [§16 Relationship to Standards](../05-reference/16-relationship-to-standards.md) |
| CROSS-5 | MUST | Prior to accepting delegation tokens from a remote Guardian, the receiving Guardian **MUST** have a registered trust relationship with the issuing Guardian. The trust relationship **MUST** include: the issuing Guardian's identity, the verification mechanism (public key for asymmetric signing, OAuth introspection endpoint, or shared channel identifier), and the scope of delegations that will be accepted. This registration **MUST** be documented in the conformance statement for Level 3 cross-system deployments. Ad-hoc trust establishment (accepting tokens from unknown Guardians) is **NOT** permitted | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CROSS-5a | MUST | Trust relationship bootstrap (**how** CROSS-5 registrations are established) **MUST** meet the following requirements: (a) trust relationships between Guardians **MUST** be registered through the Guardian's administrative interface by the human principal or an authorized administrative system — runtime trust establishment initiated by an agent, tool, or delegation token is **NOT** permitted. For the purposes of this requirement, an **authorized administrative system** is one whose identity has been verified through a mechanism independent of the secret access channel (e.g., verified by the human principal via the Guardian's administrative interface, an organization-wide infrastructure registry, or a hardware identity mechanism such as a TPM attestation or HSM certificate); administrative systems MUST NOT self-assert their authorization; the human principal MUST explicitly register each authorized administrative system in the Guardian's administrative configuration before that system may register trust relationships; and the set of authorized administrative systems MUST be enumerated in the conformance statement; (b) each trust registration event **MUST** be audit-logged with the human principal's identity, the issuing Guardian's identity, the verification mechanism registered, and the delegation scope accepted; (c) trust relationship revocation (removing a registered Guardian's trust) **MUST** take effect immediately — all subsequent requests from the revoked Guardian **MUST** be rejected, including requests carrying tokens issued before the revocation; (d) trust relationship metadata (registered Guardian identities, scopes, and verification material) **MUST** be stored in the Guardian's administrative configuration, not in the path of regular secret access requests. The conformance statement **MUST** document the process by which trust relationships are established and revoked | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CROSS-6 | MUST | Cross-system delegation relies on synchronized clocks for token expiry validation. Guardian instances participating in cross-system delegation **MUST** synchronize their clocks to a reliable time source (NTP, GPS-disciplined clock, or equivalent hardware time source). Maximum acceptable clock skew between participating Guardian instances is 30 seconds. Implementations **MAY** apply an additional clock skew tolerance to token expiry validation to account for propagation delay (RECOMMENDED: 30 seconds; MUST NOT exceed the minimum supported token TTL for the deployment). Guardian instances **MUST** refuse to issue or accept delegation tokens if their clock synchronization status is unknown or their clock skew exceeds the configured maximum | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |

> **Note:** Transport-level requirements (TLS 1.3, mTLS) for cross-system communication are defined in TOPO-1 and TOPO-2 ([§3.6.4](../01-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)) and are not restated here.

```
Machine A (Agent)                Machine B (Guardian)
┌─────────────────┐              ┌─────────────────┐
│  Agent A        │   TLS 1.3    │  Guardian       │
│                 │◄────────────►│                 │
│  Del. token     │   (TOPO-1)   │  Secret store   │
└─────────────────┘              └─────────────────┘
      │                                │
      │ Full chain context (CROSS-1)   │ Independent audit (CROSS-2)
      └────────────────────────────────┘
```

## 12.5 Service-Mediated Secret Access (Informative)

> **Note:** This subsection is informative. It identifies a related architectural pattern but does not define normative requirements. The protocol and lifecycle mechanisms for service-mediated access are deferred to a future revision of this standard.

A distinct but related problem arises with **shared services**: infrastructure components that perform work on behalf of many users and agents (CI/CD pipelines, notification services, orchestration platforms). The shared service needs temporary access to the user's secret, not its own, to perform an operation.

```
┌─────────────┐     invokes      ┌─────────────────┐     uses      ┌─────────────┐
│  User/      │ ──────────────►  │  Shared         │ ────────────► │  External   │
│  Agent      │                  │  Service        │               │  Service    │
└─────────────┘                  └─────────────────┘               └─────────────┘
     │                                   │
     │     needs user's credential       │
     └───────────────────────────────────┘
```

The following design principles are anticipated for future normative treatment. Each principle maps to an existing design principle from [§5](../02-principles/05-design-principles.md), demonstrating that service-mediated access is a specialization of the standard's core model, not a novel construct:

| ID | Principle | Grounding |
|----|-----------|-----------|
| SMA-1 | **No credential retention**: Service must not persist user secrets beyond operation scope | [§5.2 Minimal Disclosure](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure); mitigates [TS-13](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-2 | **Single-use, time-bounded**: Access constrained to single use or tight time window | DEL-12, DEL-18; mitigates [TS-13](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-3 | **User-initiated approval**: User approves before service receives secret | [§5.6 Human Supremacy](../02-principles/05-design-principles.md#56-principle-of-human-supremacy), [§10 Approval Policies](10-approval-policies.md); mitigates [TS-13](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-4 | **Scope attenuation**: Service receives only minimum entries needed | [§5.2 Minimal Disclosure](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure), DEL-4; mitigates [TS-14](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-5 | **Originating user visibility**: User can observe access regardless of service's own logging | [§5.6 Human Supremacy](../02-principles/05-design-principles.md#56-principle-of-human-supremacy), [§15 Audit & Observability](../05-reference/15-audit-observability.md) |
| SMA-6 | **Service identity separation**: Service identity distinct from user identity | [§4.2 Core Terms](../01-foundations/04-core-concepts.md#42-core-terms) |

The following protocol elements are deferred to future standard revisions: grant lifecycle protocol, JIT vs. pre-authorization models, human-in-the-loop at scale, evaluator delegation, credential translation, revocation propagation, and multi-Guardian topologies.

## 12.6 Delegation Guidance (Non-Normative)

> **Note:** The guidance in this section is non-normative. It illustrates recommended practices but does not define conformance requirements. The normative delegation requirements are defined in §12.2 and §12.3.

### Delegation Depth

Deep delegation chains are harder to audit and increase attack surface. DEL-9 **RECOMMENDS** a default maximum depth of 3. The rationale:

- **Depth 2** (Human → Agent → Tool): Standard single-agent operation. No delegation token needed; the agent's own token is sufficient.
- **Depth 3** (Human → Agent → Agent → Tool): Common orchestrator-worker pattern. One delegation token in the chain; audit trail is straightforward.
- **Depth 4+**: Each additional link increases audit complexity and widens the window for undetected scope escalation. Deployments operating at depth 4+ **SHOULD** implement enhanced monitoring (see [§15 Audit & Observability](../05-reference/15-audit-observability.md)) and set correspondingly shorter TTLs.

### Scope Selection

Delegation tokens should grant the minimum necessary access ([§5.2 Minimal Disclosure](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure)):

- **Prefer explicit entry enumeration** over wildcard scope. DEL-15 recommends against `*` scope for delegation tokens.
- **Prefer read-only permissions** unless the delegated operation requires write access. A deployment tool that only needs to read credentials should not receive `write` or `delete` permissions.

### TTL and Use Count Selection

- **Single-use (`max_uses: 1`)** for one-time operations (deploys, single API calls). This is the strongest posture: the token is consumed on first use.
- **Short TTL (1 hour or less)** for interactive delegation where the delegated agent may make multiple requests. DEL-12 recommends a 3600-second maximum.
- **Avoid multi-day TTLs.** If an operation requires a long-running delegation, re-issue short-lived delegation tokens periodically rather than issuing a single long-lived token.

## 12.7 Relationship to Conformance Levels

Full multi-agent delegation is a **Level 3** capability. However, DEL-20 (confused deputy protection) applies at all conformance levels when delegation token creation is supported. The following table maps delegation requirements to conformance levels (see [§13 Conformance](../04-conformance/13-conformance.md)):

| Capability | Level 1 | Level 2 | Level 3 |
|------------|---------|---------|---------|
| Agent-to-agent delegation (DEL-1 through DEL-12, including depth enforcement DEL-9 [MUST at Level 3] and breadth enforcement DEL-9a [MUST at Level 3]) | Not required | Not required | **MUST** be supported |
| Delegation token properties (DEL-13 through DEL-20) | Not required | Not required | **MUST** be supported |
| Cross-system delegation (CROSS-1 through CROSS-6) | Not required | Not required | **MUST** be supported |
| Confused deputy protection (DEL-20) | **MUST** be enforced if delegation token creation is supported | **MUST** be enforced if delegation token creation is supported | **MUST** be supported |
| Service-mediated access (SMA-\*) | Not required | Not required | Informative; no conformance obligation in this revision |

Implementations at Level 1 and Level 2 that do not support delegation **MUST** reject delegation token requests with an appropriate error (see [§5.5 Degradation Toward Safety](../02-principles/05-design-principles.md#55-principle-of-degradation-toward-safety)). They **MUST NOT** silently ignore delegation tokens or pass them through without validation.

---

Next: [Conformance](../04-conformance/13-conformance.md)
