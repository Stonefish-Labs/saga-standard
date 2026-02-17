# 13. Conformance

This standard defines three conformance levels. Each level builds on the previous, representing a progressively stronger security posture. Organizations **SHOULD** select a level based on their risk tolerance, compliance requirements, and deployment context.

## 13.1 Baseline Invariants

All conformance levels **MUST** satisfy the three mandatory security boundaries defined in [§3.3](../part-1-foundations/03-threat-model.md#33-security-boundaries). These properties are invariant across all levels; the conformance levels below define *additional* capabilities beyond these baseline boundaries.

| ID | Level | Requirement | References |
|----|-------|-------------|------------|
| CONF-B1 | MUST | **Boundary 1 -- Process Isolation.** Agent and Guardian **MUST** execute as separate OS processes with separate address spaces. No shared memory, file descriptors, or encryption keys between agent and Guardian processes | PROC-1 through PROC-9 ([§6.1](../part-2-principles/06-trust-boundaries.md#61-boundary-1-process-isolation-agent--guardian)); mitigates [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CONF-B2 | MUST | **Boundary 2 -- Secret Scoping.** Each token **MUST** be scoped to exactly one profile. The Guardian **MUST** verify the token on every request. Wildcard tokens, cross-profile tokens, and any mechanism that grants access to multiple profiles with a single credential are prohibited | SCOPE-1 through SCOPE-6 ([§6.2](../part-2-principles/06-trust-boundaries.md#62-boundary-2-secret-scoping-tool-a--tool-b)); mitigates [TS-4](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CONF-B3 | MUST | **Boundary 3 -- Approval Attestation.** The approval channel **MUST** use a mechanism the agent cannot intercept, forge, or influence. At Level 1, terminal-based approval is permitted provided the agent process has no access to the approval terminal's input stream. At Level 2 and above, an agent-independent channel is required per DLG-1 | DLG-1 through DLG-14 ([§6.3](../part-2-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)); mitigates [TS-3](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-9](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-16](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

**Failure mode:** If the Guardian process becomes unavailable, all secret access **MUST** be denied. The agent **MUST NOT** fall back to direct storage access, cached secrets, or any alternative retrieval mechanism ([§5.5](../part-2-principles/05-design-principles.md#55-principle-of-degradation-toward-safety), Degradation Toward Safety).

---

## 13.2 Level 1: Basic

The minimum conformance level.

> **Informative:** Suitable for development, testing, low-risk internal tools, and proof-of-concept implementations.

### Required Capabilities

All baseline invariants (§13.1), plus:

| ID | Level | Capability | Requirement | Mitigates | References |
|----|-------|------------|-------------|-----------|------------|
| CONF-L1-1 | MUST | Encrypted storage | All secret values **MUST** be encrypted at rest using an AEAD algorithm approved in [§14](../part-5-reference/14-cryptographic-requirements.md) (e.g., AES-256-GCM, ChaCha20-Poly1305) | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | CRYPTO-1 through CRYPTO-6 ([§14.1](../part-5-reference/14-cryptographic-requirements.md#141-encryption-at-rest)) |
| CONF-L1-2 | MUST | Process isolation | Agent and Guardian **MUST** execute as separate OS processes with separate address spaces. Master encryption key **MUST** reside only in Guardian process memory | [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | PROC-1 through PROC-9 ([§6.1](../part-2-principles/06-trust-boundaries.md#61-boundary-1-process-isolation-agent--guardian)) |
| CONF-L1-3 | MUST | Token authentication | Every secret request **MUST** include a bearer token scoped to exactly one profile. The Guardian **MUST** verify the token on every request | [TS-4](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-8a](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | TOKEN-1 through TOKEN-16 ([§9.2](../part-3-architecture/09-access-control.md#92-token-structure), [§9.3](../part-3-architecture/09-access-control.md#93-token-verification)) |
| CONF-L1-4 | MUST | Approval modes | Implementations **MUST** support `auto` and `prompt_once` approval modes. If a profile specifies a mode not supported at the claimed conformance level, the implementation **MUST** reject the profile configuration rather than silently degrading the approval policy | [TS-3](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-16](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | APPR-1 through APPR-5 ([§10.1](../part-3-architecture/10-approval-policies.md#101-read-approval-modes)) |
| CONF-L1-5 | MUST | Audit logging | Append-only audit log **MUST** record all access attempts with fields per [§15](../part-5-reference/15-audit-observability.md) (AUDIT-1 through AUDIT-6). Secret values **MUST NOT** appear in audit logs | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | AUDIT-1 through AUDIT-6 ([§15.1](../part-5-reference/15-audit-observability.md#151-audit-requirements)) |
| CONF-L1-6 | MUST | Fail-closed errors | All error paths **MUST** deny access. Unrecognized approval modes, missing tokens, unreachable Guardian, and failed verification **MUST** result in denial | -- | [§5.5](../part-2-principles/05-design-principles.md#55-principle-of-degradation-toward-safety) |
| CONF-L1-7 | MUST | Transport | At least one transport binding (Unix domain socket or TCP/TLS) **MUST** be supported | [TS-8a](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-8b](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | UDS-1 through UDS-5, TCP-1 through TCP-3 ([§6.4](../part-2-principles/06-trust-boundaries.md#64-transport-security)) |
| CONF-L1-8 | MUST | Package separation | Client library **MUST NOT** include server-side code. Client-only installation **MUST NOT** provide any path to bypass Guardian mediation | [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | PKG-1 through PKG-6 ([§6.5](../part-2-principles/06-trust-boundaries.md#65-package-separation)) |

### Level 1 Boundary 3 Accommodation

At Level 1, terminal-based approval is permitted for `prompt_once` and `prompt_always` modes. The agent process **MUST NOT** have access to the approval terminal's input stream. This is a Level 1 accommodation -- at Level 2 and above, an agent-independent approval channel is required (DLG-1).

---

## 13.3 Level 2: Standard

The recommended conformance level for production deployments.

> **Informative:** Suitable for production agent deployments, customer-facing agentic systems, compliance-moderate environments, and multi-environment deployments.

### Required Capabilities

All of Level 1 (§13.2), plus:

| ID | Level | Capability | Requirement | Mitigates | References |
|----|-------|------------|-------------|-----------|------------|
| CONF-L2-1 | MUST | Token expiry | Tokens **MUST** support configurable TTL-based expiration (the `expires_at` attribute) | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | TOKEN-5 ([§9.2](../part-3-architecture/09-access-control.md#92-token-structure)) |
| CONF-L2-2 | MUST | Write-back | Tools **MUST** be able to write updated values back through the Guardian. Write operations **MUST** be governed by an independently configured write approval policy | [TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | APPR-6 through APPR-11 ([§10.2](../part-3-architecture/10-approval-policies.md#102-write-approval-modes)), WRITE-1 through WRITE-6 ([§11](../part-3-architecture/11-secret-lifecycle.md)) |
| CONF-L2-3 | MUST | Agent-independent approval channel | Approval **MUST** use a channel independent of the agent process per DLG-1 -- native OS dialogs, authenticated out-of-band services, MFA-gated web dashboards, or webhook-based approval. Terminal-based approval is no longer permitted at this level | [TS-3](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-9](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-16](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | DLG-1 ([§6.3](../part-2-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)) |
| CONF-L2-4 | SHOULD | Verification codes | Approval dialogs **SHOULD** display a verification code for anti-spoofing assurance per DLG-5. Deployments satisfying the anti-spoofing property through alternative mechanisms (MFA, authenticated OOB channels) **MAY** omit verification codes at this level | [TS-9](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | DLG-5 ([§6.3](../part-2-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)), [§4.4](../part-1-foundations/04-core-concepts.md#44-approval-terms) |
| CONF-L2-5 | MUST | Session caching | Session approval cache with configurable per-profile TTL **MUST** be supported. Session cache **MUST** be held in Guardian memory only -- disk persistence is prohibited. Default TTL **MUST NOT** exceed 3600 seconds | -- | SESS-1 through SESS-8 ([§10.3](../part-3-architecture/10-approval-policies.md#103-session-approval-cache)) |
| CONF-L2-6 | MUST | Full approval modes | All three read approval modes **MUST** be supported: `auto`, `prompt_once`, `prompt_always` | [TS-3](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-16](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | APPR-1 through APPR-5 ([§10.1](../part-3-architecture/10-approval-policies.md#101-read-approval-modes)) |
| CONF-L2-7 | MUST | Full write modes | All four write modes **MUST** be supported: `same`, `auto`, `deny`, `prompt_always` | [TS-5](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-10](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | APPR-6 through APPR-11 ([§10.2](../part-3-architecture/10-approval-policies.md#102-write-approval-modes)) |
| CONF-L2-8 | SHOULD | Audit queries | Audit log **SHOULD** support structured queries by profile, token, action type, and time range | -- | AUDIT-7 ([§15.7](../part-5-reference/15-audit-observability.md#157-query-capabilities)) |
| CONF-L2-9 | MUST | Multiple transports | Both Unix domain socket and TCP/TLS transport bindings **MUST** be supported | [TS-8a](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-8b](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | UDS-1 through UDS-5, TCP-1 through TCP-3, TLS-1 through TLS-5 ([§6.4](../part-2-principles/06-trust-boundaries.md#64-transport-security)) |
| CONF-L2-10 | MUST | Transport configuration | Transport endpoint **MUST** be configurable via an implementation-defined environment variable or configuration mechanism, supporting URL-based selection across deployment environments | -- | TOKEN-17 through TOKEN-23 ([§9.4](../part-3-architecture/09-access-control.md#94-token-resolution)) |

---

## 13.4 Level 3: Advanced

For high-security and compliance-driven deployments.

> **Informative:** Suitable for regulated industries (financial, healthcare), high-value credential protection, multi-tenant environments, and enterprise-scale deployments.

### Required Capabilities

All of Level 2 (§13.3), plus:

| ID | Level | Capability | Requirement | Mitigates | References |
|----|-------|------------|-------------|-----------|------------|
| CONF-L3-1 | MUST | Secure key storage | Master encryption key **MUST** be stored in platform-provided secure key storage -- OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service), hardware security module (HSM), cloud KMS, or equivalent hardware-backed or OS-protected key storage. Encrypted file with password-derived key is not sufficient at this level | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | KEY-4 ([§14.2](../part-5-reference/14-cryptographic-requirements.md#142-master-key-management)) |
| CONF-L3-2 | MUST | Delegation tokens | Multi-agent delegation **MUST** be supported per DEL-1 through DEL-19. Delegation tokens **MUST** be integrity-protected, scope-attenuating, and subject to cascade revocation | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-13](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-14](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | DEL-1 through DEL-19 ([§12.2](../part-3-architecture/12-delegation.md#122-delegation-requirements), [§12.3](../part-3-architecture/12-delegation.md#123-delegation-token-properties)) |
| CONF-L3-3 | MUST | Cross-system delegation | Agents on one system **MUST** be able to access secrets managed by a Guardian on a separate system. Cross-system requests **MUST** include full delegation chain context for end-to-end audit reconstruction. When credential federation is implemented, OAuth 2.0 ([RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)) is the **RECOMMENDED** protocol | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | CROSS-1 through CROSS-4 ([§12.4](../part-3-architecture/12-delegation.md#124-cross-system-delegation)), TOPO-1 through TOPO-8 ([§3.6.4](../part-1-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)) |
| CONF-L3-4 | MUST | Anomaly detection | Implementations **MUST** detect and alert on anomalous access patterns. At minimum, detection **MUST** cover: (1) access frequency exceeding a configured threshold per profile per time window, (2) access from previously unseen transport endpoints, and (3) access outside configured time-of-day windows. Detection **MAY** use rules-based, statistical, or machine-learning methods | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | [§15.9](../part-5-reference/15-audit-observability.md#159-anomaly-detection) |
| CONF-L3-5 | MUST | SIEM export | Audit log **MUST** support export to external Security Information and Event Management (SIEM) systems via webhook delivery, file export, or direct integration | -- | AUDIT-8 ([§15.8](../part-5-reference/15-audit-observability.md#158-siem-integration)) |
| CONF-L3-6 | SHOULD | Rotation enforcement | Implementations **SHOULD** support credential rotation policy enforcement -- configurable maximum credential age per profile, with alerts or automatic denial when rotation is overdue | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | [§14.2](../part-5-reference/14-cryptographic-requirements.md#142-master-key-management) |
| CONF-L3-7 | SHOULD | Out-of-band revocation | Token and session revocation **SHOULD** be supported via external channels (webhook, chat integration, authenticated API) in addition to the implementation's administrative interface | -- | TOKEN-13, TOKEN-27 ([§9.5](../part-3-architecture/09-access-control.md#95-token-lifecycle)) |
| CONF-L3-8 | MUST | Mutual TLS | All Guardian communication over network transports **MUST** use mutual TLS (mTLS) for caller authentication in addition to token-based authentication | [TS-8b](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | TOPO-2 ([§3.6.4](../part-1-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)), TLS-2 ([§6.4](../part-2-principles/06-trust-boundaries.md#64-transport-security)) |
| CONF-L3-9 | MUST | Webhook approval | Implementations **MUST** support webhook-based approval for headless environments per WHOOK-1 through WHOOK-8 | [TS-3](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | HEAD-1 through HEAD-5 ([§10.5](../part-3-architecture/10-approval-policies.md#105-headless-operation)), WHOOK-1 through WHOOK-8 ([§10.6](../part-3-architecture/10-approval-policies.md#106-webhook-based-approval)) |
| CONF-L3-10 | MUST | Tool registration | Guardian **MUST** maintain a registry of authorized tool identities (binary hash, path, or code-signing certificate) and **MUST** refuse secret requests from unregistered tools | [TS-15](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | [§3.5.1](../part-1-foundations/03-threat-model.md#351-tool-substitution-ts-15) |
| CONF-L3-11 | MUST | Approval fatigue controls | Implementations **MUST** enforce configurable rate limits on approval requests per profile per time window. After a configurable number of approvals within a session, implementations **MUST** require escalated confirmation (e.g., re-entering a passphrase, biometric confirmation, or a mandatory delay before the Approve action becomes active) | [TS-17](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | [§3.5.3](../part-1-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17) |
| CONF-L3-12 | MUST | Verification codes | Approval dialogs **MUST** display a verification code for anti-spoofing assurance per DLG-5 | [TS-9](../part-1-foundations/03-threat-model.md#32-threat-scenarios) | DLG-5 ([§6.3](../part-2-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)) |

### Level 3 Delegation Constraint

Implementations at Level 1 and Level 2 that do not support delegation **MUST** reject delegation token requests with an appropriate error. They **MUST NOT** silently ignore delegation tokens or pass them through without validation ([§12.7](../part-3-architecture/12-delegation.md#127-relationship-to-conformance-levels)).

---

## 13.5 Conformance by Profile

Different profiles within the same deployment **MAY** target different conformance characteristics. The following table is non-normative guidance:

| Profile Type | Minimum Level | Recommended | Deployment Topology |
|--------------|---------------|-------------|---------------------|
| Production credentials | Level 2 | Level 3 | Remote Guardian recommended |
| Development credentials | Level 1 | Level 2 | Co-located acceptable |
| Non-secret configuration | Level 1 | Level 1 | Co-located acceptable |
| OAuth with refresh | Level 2 | Level 2 | Remote Guardian recommended |
| High-value secrets | Level 3 | Level 3 | Remote Guardian required |

See [§3.6 Guardian Deployment Topology](../part-1-foundations/03-threat-model.md#36-guardian-deployment-topology) for guidance on when to use co-located vs. remote Guardian deployment.

---

## 13.6 Protocol Conformance

Wire-level protocol conformance -- message framing, schema validation, error code handling, and transport binding compliance -- is addressed by [Annex A](../annexes/annex-a-protocol-details.md) (Informative). Annex A provides one reference wire protocol; implementations MAY use alternative wire representations provided all normative requirements in this standard are satisfied. The conformance levels defined in this section address architectural and behavioral requirements. This standard does not guarantee wire-level interoperability between independent implementations; interoperability requires agreement on a common wire protocol.

---

## 13.7 Conformance Statement

| ID | Level | Requirement |
|----|-------|-------------|
| CONF-CS-1 | MUST | Implementations claiming conformance to this standard **MUST** publish a conformance statement in the format defined below |
| CONF-CS-2 | MUST | The conformance statement **MUST** identify the claimed conformance level and assert compliance with every CONF-* requirement at that level and all lower levels |
| CONF-CS-3 | MUST | The conformance statement **MUST** document any deviations from SHOULD-level requirements, with justification |
| CONF-CS-4 | SHOULD | The conformance statement **SHOULD** be machine-readable (JSON or equivalent structured format) in addition to human-readable |

### Statement Format

```
Conformance Statement
==========================

Implementation:     [Name]
Version:            [Version]
Date:               [Date]
Conformance Level:  [Level 1 / Level 2 / Level 3]

Baseline Invariants:
  CONF-B1  Process Isolation          [Conformant / Non-Conformant]
  CONF-B2  Secret Scoping             [Conformant / Non-Conformant]
  CONF-B3  Approval Attestation       [Conformant / Non-Conformant]

Level 1 Requirements:
  CONF-L1-1  Encrypted storage        [Conformant]  Algorithm: [e.g., AES-256-GCM]
  CONF-L1-2  Process isolation        [Conformant]
  CONF-L1-3  Token authentication     [Conformant]
  CONF-L1-4  Approval modes           [Conformant]  Modes: [e.g., auto, prompt_once]
  CONF-L1-5  Audit logging            [Conformant]
  CONF-L1-6  Fail-closed errors       [Conformant]
  CONF-L1-7  Transport                [Conformant]  Transports: [e.g., Unix socket]
  CONF-L1-8  Package separation       [Conformant]

Level 2 Requirements (if claiming Level 2+):
  CONF-L2-1  Token expiry             [Conformant / N/A]
  CONF-L2-2  Write-back               [Conformant / N/A]
  CONF-L2-3  Agent-independent approval [Conformant / N/A]  Channel: [e.g., native OS dialog]
  CONF-L2-4  Verification codes       [Conformant / Deviation]
  CONF-L2-5  Session caching          [Conformant / N/A]
  CONF-L2-6  Full approval modes      [Conformant / N/A]
  CONF-L2-7  Full write modes         [Conformant / N/A]
  CONF-L2-8  Audit queries            [Conformant / Deviation]
  CONF-L2-9  Multiple transports      [Conformant / N/A]
  CONF-L2-10 Transport configuration  [Conformant / N/A]

Level 3 Requirements (if claiming Level 3):
  CONF-L3-1  Secure key storage       [Conformant / N/A]  Mechanism: [e.g., macOS Keychain]
  CONF-L3-2  Delegation tokens        [Conformant / N/A]
  CONF-L3-3  Cross-system delegation  [Conformant / N/A]
  CONF-L3-4  Anomaly detection        [Conformant / N/A]  Methods: [e.g., rate, endpoint, time]
  CONF-L3-5  SIEM export              [Conformant / N/A]
  CONF-L3-6  Rotation enforcement     [Conformant / Deviation]
  CONF-L3-7  Out-of-band revocation   [Conformant / Deviation]
  CONF-L3-8  Mutual TLS              [Conformant / N/A]
  CONF-L3-9  Webhook approval         [Conformant / N/A]
  CONF-L3-10 Tool registration        [Conformant / N/A]
  CONF-L3-11 Approval fatigue controls [Conformant / N/A]
  CONF-L3-12 Verification codes       [Conformant / N/A]

Deviations:
  [Requirement ID]  [Justification]  [Compensating control]

Notes:
  [Implementation-specific notes or extensions]
```

---

## 13.8 Verification

### Self-Verification

| ID | Level | Requirement |
|----|-------|-------------|
| CONF-VER-1 | MUST | Implementations **MUST** verify conformance by testing each CONF-* requirement at the claimed level and all lower levels |
| CONF-VER-2 | MUST | For each CONF-* requirement, the implementation **MUST** produce verifiable evidence of conformance: test results, configuration artifacts, or architectural documentation demonstrating the requirement is satisfied |
| CONF-VER-3 | MUST | Any deviations from requirements **MUST** be documented in the conformance statement (CONF-CS-3) with justification and compensating controls |
| CONF-VER-4 | SHOULD | Implementations **SHOULD** maintain an automated test suite covering each CONF-* requirement |

### Third-Party Verification

For compliance-critical deployments, third-party verification **SHOULD** include:

| ID | Level | Requirement |
|----|-------|-------------|
| CONF-VER-5 | SHOULD | The verifier **SHOULD** be a security auditor with experience in secret management systems and familiarity with this standard |
| CONF-VER-6 | SHOULD | The implementation **SHOULD** provide: (1) architecture documentation mapping components to the three-party model ([§4.1](../part-1-foundations/04-core-concepts.md#41-the-three-party-model)), (2) the conformance statement, (3) test results for each CONF-* requirement, and (4) audit log samples demonstrating logging fidelity |
| CONF-VER-7 | SHOULD | The verifier **SHOULD** test failure modes -- Guardian unavailability, token revocation, approval channel failure -- to confirm fail-closed behavior (CONF-L1-6, [§5.5](../part-2-principles/05-design-principles.md#55-principle-of-degradation-toward-safety)) |
| CONF-VER-8 | SHOULD | The verifier **SHOULD** attempt at least one boundary violation per boundary: unauthorized cross-profile access (Boundary 2), agent-initiated approval bypass (Boundary 3), and direct storage access bypassing the Guardian (Boundary 1) |

### Continuous Verification

Conformance is not a one-time event:

| ID | Level | Requirement |
|----|-------|-------------|
| CONF-VER-9 | SHOULD | Implementations **SHOULD** include automated regression tests for each CONF-* requirement in their CI/CD pipeline |
| CONF-VER-10 | SHOULD | Audit logs **SHOULD** be reviewed regularly for anomalous patterns, with frequency determined by the conformance level (Level 3 deployments **SHOULD** review at least weekly) |
| CONF-VER-11 | SHOULD | Architecture reviews **SHOULD** be conducted after significant changes to the deployment topology, trust boundaries, or Guardian configuration |
| CONF-VER-12 | MUST | After a security incident involving secret exposure or unauthorized access, the implementation **MUST** re-verify conformance for all affected boundaries and publish an updated conformance statement |

---

## 13.9 Non-Conformance

If an implementation cannot meet a requirement at its claimed conformance level, the following process **MUST** be followed:

| ID | Level | Requirement |
|----|-------|-------------|
| CONF-NC-1 | MUST | The specific CONF-* requirement that is not met **MUST** be documented, including the reason |
| CONF-NC-2 | MUST | The security risk introduced by not meeting the requirement **MUST** be assessed with reference to the threat scenarios (TS-*) that the requirement mitigates |
| CONF-NC-3 | SHOULD | Compensating controls that reduce the risk of the gap **SHOULD** be applied and documented |
| CONF-NC-4 | SHOULD | A remediation plan with timeline **SHOULD** be established |
| CONF-NC-5 | MUST | An authorized representative of the deploying organization **MUST** formally accept the risk of non-conformance. The acceptance, the gap, the risk assessment, and any compensating controls **MUST** be recorded in the conformance statement |

Non-conformance with documented compensating controls and formal risk acceptance is better than non-conformance without acknowledgment.

---

## Summary

| Level | Baseline + Capabilities | Threat Coverage | Deployment Context |
|-------|------------------------|-----------------|-------------------|
| **Level 1** | Three boundaries + encrypted storage, token auth, basic approval, audit, fail-closed | TS-3, TS-4, TS-5, TS-6, TS-7, TS-8a, TS-11, TS-12, TS-15, TS-16, TS-18 | Development, testing, low-risk |
| **Level 2** | Level 1 + agent-independent approval, token TTL, write-back, session caching, full modes, multi-transport | Level 1 + TS-8b, TS-9, TS-10 | Production deployments |
| **Level 3** | Level 2 + secure key storage, delegation, cross-system, anomaly detection, SIEM, mTLS, tool registration, fatigue controls | Level 2 + TS-12 (delegation), TS-13, TS-14, TS-17 (fatigue) | High-security, regulated, enterprise |

---

Next: [Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md)
