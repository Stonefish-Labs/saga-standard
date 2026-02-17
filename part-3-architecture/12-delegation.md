# 12. Delegation and Cross-System Propagation

Multi-agent architectures introduce a cascading delegation problem: when Agent A delegates work to Agent B, secrets must flow through the chain without exposure, loss of audit trail, or privilege escalation. This section defines the normative requirements for secret delegation in multi-agent systems.

The delegation model addresses three threat scenarios from [§3.2](../part-1-foundations/03-threat-model.md#32-threat-scenarios):

- **[TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios)** -- Cascading agent delegation causes unaudited access
- **[TS-13](../part-1-foundations/03-threat-model.md#32-threat-scenarios)** -- Shared service retains credential beyond authorized scope
- **[TS-14](../part-1-foundations/03-threat-model.md#32-threat-scenarios)** -- Shared service escalates credential to unauthorized resources

Delegation tokens are a **Level 3** capability (see [§13.4](../part-4-conformance/13-conformance.md#134-level-3-advanced)). Implementations at Level 1 and Level 2 are not required to support multi-agent delegation. Level 3 implementations **MUST** support the delegation requirements defined in this section.

The SAGA delegation model shares principles with established delegation mechanisms (OAuth 2.0 Token Exchange [RFC 8693], capability-based attenuation [Macaroons], identity delegation [SPIFFE]). SAGA differs in that delegation tokens are purely authorization artifacts -- they never contain secret values -- and the Guardian validates the full delegation chain on every request rather than relying on cryptographic capability chaining. See [§16 Relationship to Standards](../part-5-reference/16-relationship-to-standards.md).

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

- Agent A cannot pass secret *values* to Agent B -- this would violate process isolation ([Boundary 1](../part-2-principles/06-trust-boundaries.md))
- Agent B needs independent authorization from the Guardian
- The audit trail must show the full delegation chain from human principal to final tool

Delegation is an *authorization* problem, not a *secret distribution* problem. The delegation token carries the right to request secrets -- never the secrets themselves.

> **Security note:** Delegation tokens are bearer credentials, subject to the same interception and replay risks as agent tokens ([TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios)). The mitigations are the same: short TTLs (DEL-12), single-use where possible (DEL-11), and transport encryption ([TOPO-1](../part-1-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)).

## 12.2 Delegation Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| DEL-1 | MUST | An agent **MUST NOT** pass secret values to another agent. Each agent **MUST** independently request secrets from the Guardian | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-2 | MUST | When Agent A delegates work to Agent B, Agent A **MUST** request a delegation token from the Guardian. The Guardian **MUST** create the delegation token, constrained to a subset of Agent A's authorized scope, and return it to Agent A for delivery to Agent B. Agent A **MUST NOT** create delegation tokens itself | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-14](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-3 | MUST | Delegation tokens **MUST NOT** contain secret values. A delegation token authorizes Agent B to request specific secrets from the Guardian; it does not carry or transmit those secrets | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-4 | MUST | Delegation tokens **MUST NOT** exceed the scope of the parent token. The set of accessible profiles, entries, and permissions in the delegation token **MUST** be a subset of -- or equal to -- those of the parent token | [TS-14](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-5 | MUST | Delegation tokens **MUST NOT** outlive the parent token. The expiration of a delegation token **MUST** be before or equal to the expiration of the parent token | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-6 | MUST | The Guardian **MUST** validate the full delegation chain -- from the delegation token back to the originating human-principal-issued token -- on every request. Caching of parent chain validity is prohibited | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-7 | MUST | When a parent token is revoked or expires, all delegation tokens derived from it **MUST** be immediately invalidated (cascade revocation). In-flight operations authorized under the revoked delegation **MAY** complete, but new requests **MUST** be denied. See [§5.6 Human Supremacy](../part-2-principles/05-design-principles.md#56-principle-of-human-supremacy) | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-8 | MUST | Each agent in a delegation chain **MUST** appear as a distinct entity in the audit log. The audit entry for each delegated access **MUST** include: the delegation token ID, the parent token ID, the delegation chain depth, and the originating human principal. See [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-9 | SHOULD | Implementations **SHOULD** enforce a configurable maximum delegation chain depth. The **RECOMMENDED** default maximum depth is 3 | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-10 | MUST | Delegation tokens **MUST** be integrity-protected using a mechanism specified in [§14 Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md). The integrity key **MUST** be held exclusively by the Guardian and **MUST NOT** be shared with agents or tools | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-11 | MUST | When a delegation token specifies a maximum use count, the Guardian **MUST** enforce the count atomically -- concurrent requests **MUST NOT** exceed the configured maximum | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| DEL-12 | SHOULD | Delegation token TTLs **SHOULD NOT** exceed 3600 seconds (1 hour). TTLs exceeding one calendar day are **NOT RECOMMENDED**. Shorter TTLs limit the exposure window if a delegation token is intercepted ([TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios)) | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

## 12.3 Delegation Token Properties

A delegation token **MUST** have the following properties. The concrete token structure -- field names, encoding, and serialization format -- is provided in [Annex A](../annexes/annex-a-protocol-details.md).

| ID | Level | Requirement |
|----|-------|-------------|
| DEL-13 | MUST | Each delegation token **MUST** have a unique identifier, generated from a cryptographically secure random source (see [§14 Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md)) |
| DEL-14 | MUST | Each delegation token **MUST** reference its parent token's identifier, enabling the Guardian to reconstruct the full delegation chain |
| DEL-15 | MUST | Each delegation token **MUST** specify the profile(s) and entry keys it authorizes. Wildcard entry scope (`*`) is **NOT RECOMMENDED**; explicit entry enumeration **SHOULD** be preferred to enforce the [Principle of Minimal Disclosure](../part-2-principles/05-design-principles.md#52-principle-of-minimal-disclosure) |
| DEL-16 | MUST | Each delegation token **MUST** specify the permitted operations (`read`, `write`, `delete`). The permitted operations **MUST** be a subset of the parent token's permissions (DEL-4) |
| DEL-17 | MUST | Each delegation token **MUST** include an issuance timestamp and an expiration timestamp, both in UTC |
| DEL-18 | MAY | A delegation token **MAY** include a maximum use count. If present, the Guardian **MUST** enforce it atomically (DEL-11). A use count of 1 (single-use) is **RECOMMENDED** for one-time operations |
| DEL-19 | MUST | Each delegation token **MUST** include an integrity signature generated by the Guardian. The signature **MUST** cover all token fields. See [§14 Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md) for algorithm and key management |

> **Note:** An illustrative token structure with field names and a JSON example is provided in [Annex A](../annexes/annex-a-protocol-details.md). This standard defines the required properties; Annex A illustrates one conformant wire format.

## 12.4 Cross-System Delegation

Cross-system delegation builds on the remote Guardian deployment topology defined in [§3.6](../part-1-foundations/03-threat-model.md#36-guardian-deployment-topology). The TOPO-\* requirements (TOPO-1 through TOPO-8) apply to all remote Guardian deployments. The following requirements address delegation-specific concerns when agents on one system access secrets managed by a Guardian on a separate system.

| ID | Level | Requirement | Cross-Reference |
|----|-------|-------------|-----------------|
| CROSS-1 | MUST | Cross-system delegation requests **MUST** include the full delegation chain context -- all token IDs from the delegation token back to the originating principal-issued token -- to enable end-to-end audit reconstruction | DEL-8, [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |
| CROSS-2 | MUST | Each system in a cross-system delegation **MUST** maintain its own audit log recording all delegation requests and their outcomes | [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |
| CROSS-3 | MUST | Secrets obtained via cross-system delegation **MUST NOT** be cached or persisted on intermediate systems | [TOPO-6](../part-1-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment) |
| CROSS-4 | SHOULD | Cross-system credential federation **SHOULD** be supported. When federation is implemented, OAuth 2.0 ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)) is the **RECOMMENDED** protocol | [§16 Relationship to Standards](../part-5-reference/16-relationship-to-standards.md) |

> **Note:** Transport-level requirements (TLS 1.3, mTLS) for cross-system communication are defined in TOPO-1 and TOPO-2 ([§3.6.4](../part-1-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)) and are not restated here.

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

A distinct but related problem arises with **shared services**: infrastructure components that perform work on behalf of many users and agents (CI/CD pipelines, notification services, orchestration platforms). The shared service needs temporary access to the user's secret -- not its own -- to perform an operation.

```
┌─────────────┐     invokes      ┌─────────────────┐     uses      ┌─────────────┐
│  User/      │ ──────────────►  │  Shared         │ ────────────► │  External   │
│  Agent      │                  │  Service        │               │  Service    │
└─────────────┘                  └─────────────────┘               └─────────────┘
     │                                   │
     │     needs user's credential       │
     └───────────────────────────────────┘
```

The following design principles are anticipated for future normative treatment. Each principle maps to an existing design principle from [§5](../part-2-principles/05-design-principles.md), demonstrating that service-mediated access is a specialization of the standard's core model, not a novel construct:

| ID | Principle | Grounding |
|----|-----------|-----------|
| SMA-1 | **No credential retention** -- Service must not persist user secrets beyond operation scope | [§5.2 Minimal Disclosure](../part-2-principles/05-design-principles.md#52-principle-of-minimal-disclosure); mitigates [TS-13](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-2 | **Single-use, time-bounded** -- Access constrained to single use or tight time window | DEL-12, DEL-18; mitigates [TS-13](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-3 | **User-initiated approval** -- User approves before service receives secret | [§5.6 Human Supremacy](../part-2-principles/05-design-principles.md#56-principle-of-human-supremacy), [§10 Approval Policies](10-approval-policies.md); mitigates [TS-13](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-4 | **Scope attenuation** -- Service receives only minimum entries needed | [§5.2 Minimal Disclosure](../part-2-principles/05-design-principles.md#52-principle-of-minimal-disclosure), DEL-4; mitigates [TS-14](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SMA-5 | **Originating user visibility** -- User can observe access regardless of service's own logging | [§5.6 Human Supremacy](../part-2-principles/05-design-principles.md#56-principle-of-human-supremacy), [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |
| SMA-6 | **Service identity separation** -- Service identity distinct from user identity | [§4.2 Core Terms](../part-1-foundations/04-core-concepts.md#42-core-terms) |

The following protocol elements are deferred to future standard revisions: grant lifecycle protocol, JIT vs. pre-authorization models, human-in-the-loop at scale, evaluator delegation, credential translation, revocation propagation, and multi-Guardian topologies.

## 12.6 Delegation Guidance (Non-Normative)

> **Note:** The guidance in this section is non-normative. It illustrates recommended practices but does not define conformance requirements. The normative delegation requirements are defined in §12.2 and §12.3.

### Delegation Depth

Deep delegation chains are harder to audit and increase attack surface. DEL-9 **RECOMMENDS** a default maximum depth of 3. The rationale:

- **Depth 2** (Human → Agent → Tool) -- Standard single-agent operation. No delegation token needed; the agent's own token is sufficient.
- **Depth 3** (Human → Agent → Agent → Tool) -- Common orchestrator-worker pattern. One delegation token in the chain; audit trail is straightforward.
- **Depth 4+** -- Each additional link increases audit complexity and widens the window for undetected scope escalation. Deployments operating at depth 4+ **SHOULD** implement enhanced monitoring (see [§15 Audit & Observability](../part-5-reference/15-audit-observability.md)) and set correspondingly shorter TTLs.

### Scope Selection

Delegation tokens should grant the minimum necessary access ([§5.2 Minimal Disclosure](../part-2-principles/05-design-principles.md#52-principle-of-minimal-disclosure)):

- **Prefer explicit entry enumeration** over wildcard scope. DEL-15 recommends against `*` scope for delegation tokens.
- **Prefer read-only permissions** unless the delegated operation requires write access. A deployment tool that only needs to read credentials should not receive `write` or `delete` permissions.

### TTL and Use Count Selection

- **Single-use (`max_uses: 1`)** for one-time operations (deploys, single API calls). This is the strongest posture -- the token is consumed on first use.
- **Short TTL (1 hour or less)** for interactive delegation where the delegated agent may make multiple requests. DEL-12 recommends a 3600-second maximum.
- **Avoid multi-day TTLs.** If an operation requires a long-running delegation, re-issue short-lived delegation tokens periodically rather than issuing a single long-lived token.

## 12.7 Relationship to Conformance Levels

Delegation is a **Level 3** capability. The following table maps delegation requirements to conformance levels (see [§13 Conformance](../part-4-conformance/13-conformance.md)):

| Capability | Level 1 | Level 2 | Level 3 |
|------------|---------|---------|---------|
| Agent-to-agent delegation (DEL-1 through DEL-12) | Not required | Not required | **MUST** be supported |
| Delegation token properties (DEL-13 through DEL-19) | Not required | Not required | **MUST** be supported |
| Cross-system delegation (CROSS-1 through CROSS-4) | Not required | Not required | **MUST** be supported |
| Maximum delegation depth enforcement (DEL-9) | Not required | Not required | **SHOULD** be supported |
| Service-mediated access (SMA-\*) | Not required | Not required | Informative -- no conformance obligation in this revision |

Implementations at Level 1 and Level 2 that do not support delegation **MUST** reject delegation token requests with an appropriate error (see [§5.5 Degradation Toward Safety](../part-2-principles/05-design-principles.md#55-principle-of-degradation-toward-safety)). They **MUST NOT** silently ignore delegation tokens or pass them through without validation.

---

Next: [Conformance](../part-4-conformance/13-conformance.md)
