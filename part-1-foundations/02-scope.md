# 2. Scope

## 2.1 In Scope

This standard applies to any system where:

- An AI model (LLM, reasoning engine, planning system) triggers operations that require secrets for authentication or cryptographic operations
- A Guardian (or equivalent mediator) controls access to the encrypted secret store and enforces authorization policies on behalf of the human principal
- The secrets are owned by -- or under the authority of -- a human principal who may not be present at the time of use. This includes secrets provisioned by automated systems (e.g., cloud-to-cloud API keys, service account credentials) where a human principal retains accountability and override authority over their use
- Multiple tools, skills, or services may require different secrets within the same agent session
- Secrets may need to be updated (written back) during the course of agent operation

### Specific Scenarios

| Scenario | Example Secrets |
|----------|-----------------|
| MCP servers accessing third-party APIs | API keys, OAuth tokens |
| Agent orchestration framework tools | Service credentials, webhook URLs |
| Browser automation agents | Authentication cookies, OAuth tokens |
| Multi-agent systems | Shared secrets passed between agents |
| Autonomous coding agents | GitHub tokens, cloud provider keys, deploy keys |
| Customer service agents | CRM credentials, communication platform tokens |
| Infrastructure automation agents | Database credentials, SSH private keys, TLS private keys |

### Secret Types Covered

This standard covers the following categories of secrets -- information that, alone or in combination, grants access to a resource or enables a privileged capability (see [§1 Introduction](01-introduction.md) for the full definition):

| Type | Examples |
|------|----------|
| **Credentials** | API keys, passwords, access tokens |
| **OAuth artifacts** | Access tokens, refresh tokens, client secrets |
| **Cryptographic keys** | Private keys, signing keys, encryption keys |
| **Embedded-credential configuration** | Connection strings with passwords, webhook URLs with embedded tokens |
| **Session credentials** | Session tokens, authentication cookies, temporary credentials |

## 2.2 Out of Scope

### Model Safety Alignment

Jailbreaking defense, prompt injection prevention at the model level, and output filtering are addressed by model-level controls and training. This standard assumes these may fail and provides architectural defenses that work regardless.

### Agent Identity and Authentication

How the agent proves *its own* identity to external systems -- and how agentic identity is established, attested, and verified -- is an active area of standardization outside the scope of this document. This standard is deliberately agnostic to the agent identity mechanism. It addresses what happens after the agent is authenticated: how it accesses secrets to do work on the human principal's behalf.

### Network Transport Encryption

TLS, mTLS between services, and network-level encryption are addressed by existing transport security standards. The standard operates above the transport layer.

### Organizational Secrets Governance

Who may create which profiles, compliance with SOC2/ISO27001, and organizational policy enforcement are governance concerns. This standard provides the technical foundation but does not prescribe organizational structure.

### Hardware Security Modules (HSM) Integration

HSM integration is an implementation detail. The standard is compatible with HSM-backed key storage but does not require it. The standard focuses on the architectural patterns that work regardless of how encryption keys are stored and managed.

### Secret Generation and Strength

This standard does not prescribe how secrets should be generated or what strength requirements they should meet. The standard manages secrets you provide; it does not create them.

## 2.3 Protocol Details (Annex A)

Wire-level protocol details, JSON schema definitions, example flows, and reference architectures are provided in [Annex A](../annexes/annex-a-protocol-details.md) (Informative). This standard defines *what* a conformant system must do; Annex A illustrates *how* to implement it at the wire level. Annex A does not carry normative weight — conformance is assessed against this standard alone.

This standard does not guarantee wire-level interoperability between independent implementations. Interoperability requires that implementations agree on a common wire protocol; Annex A provides one such protocol as a reference. Implementers may use alternative wire representations provided all normative requirements in this standard are satisfied.

## 2.4 Boundary with Related Standards

```
┌──────────────────────────────────────────────────────────────────┐
│                      Organizational Policy                       │
│  (who can create profiles, compliance requirements, audit        │
│   review cadence, rotation policies)                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      This Standard                         │  │
│  │  (secret isolation, access control, approval, audit,       │  │
│  │   delegation, lifecycle management)                        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
├───────────────────────────────┬──────────────────────────────────┤
│  Transport Security           │  Agent Identity                  │
│  (TLS, mTLS)                  │  (OAuth 2.1, etc.)               │
├───────────────────────────────┴──────────────────────────────────┤
│                      Model Safety Layer                          │
│  (prompt injection defense, output filtering, alignment)         │
└──────────────────────────────────────────────────────────────────┘
```

This standard sits between organizational governance and transport security. It assumes:
- Organizational policies exist to govern who can do what
- Transport security protects data in motion
- Model safety may fail (hence architectural isolation)

---

Next: [Threat Model](03-threat-model.md)
