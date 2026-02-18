# 16. Relationship to Existing Standards

> **Informative:** This section is non-normative. It provides guidance on the relationship between this standard and related standards and frameworks. Normative requirements are defined in the referenced sections. Where this section describes the standard's coverage, the authoritative requirements are in the cited sections, not in this mapping.

This standard does not exist in isolation. This section maps the standard to related standards and frameworks, clarifying what the standard provides and where other standards apply.

## 16.1 OWASP Agentic Top 10

The [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) identifies risks specific to agentic AI systems. This standard directly addresses several of these risks through architectural controls:

| OWASP Risk | Control | Standard References | Threat Scenarios |
|------------|---------|---------------------|------------------|
| **AA01: Prompt Injection** | Architectural isolation: agent never holds or receives secret values | [§5.1 Mediated Access](../02-principles/05-design-principles.md#51-principle-of-mediated-access), [§6.1 Process Isolation](../02-principles/06-trust-boundaries.md#61-boundary-1-process-isolation-agent--guardian) | [TS-3](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| **AA02: Insecure Tool Implementation** | Token scoping, write policies, audit logging | [§9 Access Control](../03-architecture/09-access-control.md), [§10.2 Write Approval](../03-architecture/10-approval-policies.md#102-write-approval-modes), [§15 Audit](15-audit-observability.md) | [TS-4, TS-5, TS-10](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| **AA03: Excessive Permissions** | Per-profile token scoping, one-token-one-profile invariant | [§6.2 Secret Scoping](../02-principles/06-trust-boundaries.md#62-boundary-2-secret-scoping-tool-a--tool-b), [§9.2 Token Structure](../03-architecture/09-access-control.md#92-token-structure) | [TS-4](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| **AA05: Insecure Credential Storage** | Per-entry AEAD encryption, platform-secured key storage | [§14 Cryptographic Requirements](14-cryptographic-requirements.md), [§14.2 Master Key Management](14-cryptographic-requirements.md#142-master-key-management) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| **AA07: Insufficient User Oversight** | Approval tiers, verification codes, agent-independent approval channels | [§7 Autonomy Tiers](../02-principles/07-autonomy-tiers.md), [§10 Approval Policies](../03-architecture/10-approval-policies.md), [§6.3 Approval Attestation](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian) | [TS-16, TS-17](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| **AA08: Overly Broad Agent Scope** | Profile-level access control, single-profile tokens | [§6.2 Secret Scoping](../02-principles/06-trust-boundaries.md#62-boundary-2-secret-scoping-tool-a--tool-b), [§8 Secret Profiles](../03-architecture/08-secret-profiles.md) | [TS-4](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### What This Standard Does Not Address

| OWASP Risk | Reason |
|------------|--------|
| AA04: Insecure Output Handling | Addresses output sanitization for general tool outputs; this standard addresses the credential-specific subset through [§5.2 Minimal Disclosure](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure) (tool output channels must not include raw secret values) but does not address general output handling controls |
| AA06: Sensitive Data Disclosure | Addresses classification and handling of general sensitive data (PII, financial, medical); this standard addresses the credential-specific subset through [§5.2 Minimal Disclosure](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure) and [§5.3 Declared Sensitivity](../02-principles/05-design-principles.md#53-principle-of-declared-sensitivity), but general sensitive data classification is outside scope |
| AA09: Model Poisoning | Training data security and model integrity, not runtime credential management |
| AA10: Unbounded Agency | Agent capability limits and scope governance, not credential access controls |

These require complementary controls beyond the scope of this standard.

## 16.2 Model Context Protocol (MCP)

This standard complements the [Model Context Protocol](https://modelcontextprotocol.io/specification) security model. MCP defines the transport and interaction protocol between agent runtimes and tool servers; this standard defines how those tool servers securely manage the third-party credentials they need to do their work.

| MCP Provides | This Standard Adds |
|--------------|-----------|
| OAuth 2.1 transport auth between client and server | Per-tool secret scoping within a server ([§6.2](../02-principles/06-trust-boundaries.md#62-boundary-2-secret-scoping-tool-a--tool-b)) |
| Server identity verification | Secret isolation from agent reasoning loop ([§6.1](../02-principles/06-trust-boundaries.md#61-boundary-1-process-isolation-agent--guardian)) |
| Authorization grants for server capabilities | Approval policies for individual profiles ([§10](../03-architecture/10-approval-policies.md)) |
| -- | Write-back protocol for secret lifecycle ([§11](../03-architecture/11-secret-lifecycle.md)) |
| -- | Audit trail for secret access ([§15](15-audit-observability.md)) |
| -- | Human approval attestation ([§6.3](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian)) |

> **Note:** MCP's authentication model is evolving. The mapping above reflects MCP's current specification at the time of publication. Implementers should verify the current MCP specification for authentication details.

### Integration Pattern

An MCP server implementing this standard:

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Client                                                 │
│  (Agent runtime -- untrusted per §3.1)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ MCP Protocol (OAuth 2.1)
                          │ ── Boundary 1 (process isolation) ──
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Server                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Tool Implementation                                │   │
│  │  - Implements SAGA client protocol (see Annex A)    │   │
│  │  - Requests secrets from Guardian via token          │   │
│  │  - Never exposes secrets to agent                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                   ── Boundary 2 (token scoping) ──          │
└─────────────────────────┬───────────────────────────────────┘
                          │ SAGA Protocol (IPC/TLS)
                          │ (see Annex A)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Guardian Service                                           │
│  - Stores and encrypts secrets (§14)                       │
│  - Enforces approval policies (§10)                        │
│  - Mediates human approval (Boundary 3)                    │
│  - Logs all access (§15)                                   │
└─────────────────────────────────────────────────────────────┘
```

The MCP server uses MCP's OAuth for its own authentication to the MCP client, and this standard's protocol for managing the third-party secrets it needs to do its work. Trust boundaries from [§3.3](../01-foundations/03-threat-model.md#33-security-boundaries) apply at each connection: the MCP Client (agent runtime) and Guardian are separated by Boundary 1 (process isolation); the tool's secret access is scoped by Boundary 2 (token scoping); human approval is mediated by Boundary 3 (approval attestation). When the Guardian is unavailable, the tool must deny the secret request per [§5.5 Degradation Toward Safety](../02-principles/05-design-principles.md#55-principle-of-degradation-toward-safety).

## 16.3 NIST AI Risk Management Framework

This standard maps to [NIST AI Risk Management Framework](https://doi.org/10.6028/NIST.AI.100-1) (NIST AI 100-1) functions:

| NIST Function | Alignment | Standard References |
|---------------|-----------|---------------------|
| **GOVERN** | Autonomy tiers provide organizational governance framework | [§7 Autonomy Tiers](../02-principles/07-autonomy-tiers.md) |
| **MAP** | Threat model identifies credential-specific risks | [§3 Threat Model](../01-foundations/03-threat-model.md) |
| **MEASURE** | Audit logging provides quantitative access measurement | [§15 Audit & Observability](15-audit-observability.md) |
| **MANAGE** | Approval policies implement runtime risk controls | [§10 Approval Policies](../03-architecture/10-approval-policies.md) |

The NIST AI RMF identifies agentic system security as an area requiring domain-specific guidance. This standard provides that guidance for the credential management dimension.

## 16.4 IETF OAuth for AI Agents

The [IETF draft on OAuth On-Behalf-Of for AI Agents](https://datatracker.ietf.org/doc/draft-ietf-oauth-on-behalf-of/) *(Internet-Draft; as this draft is not yet an RFC, implementers MUST verify the current version number at the time of implementation. The version consulted during this document's drafting was current as of February 2026 — cite as `draft-ietf-oauth-on-behalf-of-[version]` with the version retrieved from the IETF Datatracker at implementation time)* addresses *identity delegation*:

- How an agent proves it acts on behalf of a user to a third-party service
- How to represent agent identity in [OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) (RFC 6749) flows

This standard addresses *credential management*:

- How the agent's tools securely access credentials ([§5.1](../02-principles/05-design-principles.md#51-principle-of-mediated-access))
- How to store, scope, and audit credential access ([§8](../03-architecture/08-secret-profiles.md), [§9](../03-architecture/09-access-control.md), [§15](15-audit-observability.md))
- How to handle credential lifecycle (rotation, refresh) ([§11](../03-architecture/11-secret-lifecycle.md))

### Relationship

```
┌─────────────────────────────────────────────────────────────┐
│  User (Human Principal)                                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent                                                      │
│  Identity: IETF OAuth On-Behalf-Of                         │
│  "I am acting on behalf of user@example.com"               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Tool                                                       │
│  Credentials: via Guardian (§5.1 Mediated Access)          │
│  "I need the OAuth token to call the API"                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Guardian Service                                           │
│  Provides secret through mediated access protocol          │
└─────────────────────────────────────────────────────────────┘
```

The standards are complementary:
- IETF OAuth provides the identity assertion protocol, proving *who* the agent acts for
- This standard provides the credential storage and mediation, controlling *how* the agent's tools access secrets

## 16.5 Traditional Secrets Management

This standard is not a replacement for traditional secrets managers. It is a specialized layer for agentic systems that addresses the three-party trust problem ([§4.1](../01-foundations/04-core-concepts.md#41-the-three-party-model)) that traditional systems were not designed for.

| System | Trust Model | Applicability |
|--------|-------------|-------------------|
| HashiCorp Vault | Process is trusted principal | Not directly applicable; assumes consumer is authorized entity |
| AWS Secrets Manager | IAM role is trusted principal | Not directly applicable; assumes role-based identity is authorization |
| Azure Key Vault | Managed identity is trusted | Not directly applicable; assumes managed identity is authorization |
| 1Password/Bitwarden | Human user is trusted | Not directly applicable; assumes human is direct consumer |

### What's Different

Traditional systems assume:
- The consuming entity is the authorized entity (two-party model)
- Single trust boundary (storage → consumer)
- Human or service identity is the access control basis

This standard assumes:
- The consuming entity (tool) is NOT the authorizing entity (human); see [§4.1 Three-Party Model](../01-foundations/04-core-concepts.md#41-the-three-party-model)
- Three-party trust model (human → agent → tool) with an untrusted intermediary; see [§3.1 Threat Actors](../01-foundations/03-threat-model.md#31-threat-actors)
- Agent is untrusted, tool is semi-trusted, Guardian is trusted; see [§6 Trust Boundaries](../02-principles/06-trust-boundaries.md)

### Integration

Implementations can use traditional secrets managers as the Guardian's backing store:

```
Guardian → HashiCorp Vault → Storage
```

The Guardian still enforces the standard's policies ([§5 Design Principles](../02-principles/05-design-principles.md), [§9 Access Control](../03-architecture/09-access-control.md), [§10 Approval Policies](../03-architecture/10-approval-policies.md)); the traditional secrets manager provides the storage backend. The standard's architectural requirements (process isolation, token scoping, approval attestation, audit logging) are enforced by the Guardian regardless of the backing store.

## 16.6 Kerberos

[Kerberos](https://datatracker.ietf.org/doc/html/rfc4120) (RFC 4120) constrained delegation established precedent for the principle of limited, mediated credential issuance. This standard borrows the conceptual model (not the protocol mechanics) from Kerberos:

| Kerberos Concept | Conceptual Parallel | Distinction |
|------------------|---------------------|-------------|
| Ticket Granting Ticket (TGT) | Session approval ([§10.3](../03-architecture/10-approval-policies.md#103-session-approval-cache)) | A TGT is a cryptographic credential; a session approval is a cached authorization decision held in Guardian memory. The TGT is bearer-portable; the session approval is Guardian-internal. |
| Service Ticket | Profile access grant | A service ticket is issued to the client for presentation to the service; a profile access grant is mediated entirely by the Guardian (the tool presents a token, not a ticket). |
| Constrained Delegation | Scoped delegation tokens ([§12](../03-architecture/12-delegation.md)) | Kerberos constrains delegation by service principal name; this standard constrains by profile scope and entry keys. Both enforce non-amplification. |
| Key Distribution Center (KDC) | Guardian Service ([§4.2](../01-foundations/04-core-concepts.md#42-core-terms)) | The KDC authenticates principals and issues tickets cryptographically; the Guardian mediates secret access and enforces policy. Both serve as trusted third parties, but the Guardian's role extends to approval attestation and audit. |

These are conceptual parallels, not protocol equivalencies. This standard does not implement Kerberos ticket semantics, realm federation, or mutual authentication via ticket exchange. The principle borrowed from Kerberos is that credential issuance should be mediated by a trusted intermediary that enforces scope constraints, the same principle expressed in [§5.1 Mediated Access](../02-principles/05-design-principles.md#51-principle-of-mediated-access).

## 16.7 SPIFFE/SPIRE

[SPIFFE](https://github.com/spiffe/spiffe/blob/v1.0.0/standards/SPIFFE.md) (Secure Production Identity Framework for Everyone, v1.0.0) provides cryptographic workload identity in distributed systems. The SPIFFE specification is maintained by the CNCF; the canonical project page is [spiffe.io](https://spiffe.io/). [SPIRE](https://github.com/spiffe/spire) implements SPIFFE through workload attestation, verifying the identity of a running process based on platform-specific evidence (kernel metadata, container orchestration data, cloud provider identity documents).

### Relationship to This Standard

SPIFFE addresses *workload identity* (proving that a running process is who it claims to be). This standard addresses *secret mediation* (controlling how authenticated tools access credentials through a trusted intermediary). The concerns are complementary:

- **Tool authentication:** SPIFFE IDs could serve as the tool identity mechanism for Guardian authentication, strengthening the tool provenance verification that mitigates [TS-15 (Tool Substitution)](../01-foundations/03-threat-model.md#351-tool-substitution-ts-15). A Guardian that verifies a tool's SPIFFE ID before honoring token-based requests adds a layer of identity assurance beyond bearer tokens alone.

- **Guardian authentication:** In remote deployments ([§3.6](../01-foundations/03-threat-model.md#36-guardian-deployment-topology)), SPIFFE-based mutual authentication between tools and the Guardian could supplement or replace the mTLS requirements in TOPO-2 ([§3.6.4](../01-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment)).

- **Trust model distinction:** SPIFFE assumes the workload *is* the trusted principal; once identity is established, the workload receives secrets directly. This standard assumes the workload (tool) is *semi-trusted* and access is mediated through a Guardian that enforces approval policies. SPIFFE provides identity; this standard provides mediation.

Future revisions of this standard may define normative integration with SPIFFE IDs for service-to-Guardian authentication in multi-machine deployments.

## 16.8 References

The following external standards and specifications are referenced in this section:

| Standard | Identifier | Reference |
|----------|-----------|-----------|
| OWASP Top 10 for Agentic Applications | v1.0 (2026) | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ |
| Model Context Protocol | Current specification | https://modelcontextprotocol.io/specification |
| NIST AI Risk Management Framework | NIST AI 100-1 | https://doi.org/10.6028/NIST.AI.100-1 |
| IETF OAuth On-Behalf-Of for AI Agents | Internet-Draft (version as of February 2026; verify current version at implementation time) | https://datatracker.ietf.org/doc/draft-ietf-oauth-on-behalf-of/ |
| OAuth 2.0 Authorization Framework | RFC 6749 | https://datatracker.ietf.org/doc/html/rfc6749 |
| The Kerberos Network Authentication Service (V5) | RFC 4120 | https://datatracker.ietf.org/doc/html/rfc4120 |
| SPIFFE | Secure Production Identity Framework for Everyone, v1.0.0 (CNCF) | https://github.com/spiffe/spiffe/blob/v1.0.0/standards/SPIFFE.md |

> **Note:** Some referenced specifications (MCP, IETF OAuth On-Behalf-Of) are draft or evolving standards. The mappings in this section reflect the state of these specifications at the time of publication. Implementers should verify current versions.

---

Next: [Appendix A: Evaluation Criteria](../06-appendices/appendix-a-evaluation-criteria.md)
