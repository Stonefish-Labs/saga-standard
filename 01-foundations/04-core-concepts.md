# 4. Core Concepts

This section defines the terms and mental models used throughout the standard. Where definitions include architectural constraints (e.g., "must never see secret values"), the normative requirements with RFC 2119 keywords are stated in [Design Principles](../02-principles/05-design-principles.md) and [Trust Boundaries](../02-principles/06-trust-boundaries.md). Statements in this section describe the intended properties of each concept; the cited sections provide the binding requirements.

## 4.1 The Three-Party Model

The fundamental insight of this standard is that agentic systems introduce a third party into secret management:

```
Traditional Model (2-party):
┌─────────────┐                    ┌─────────────┐
│   Principal │ ──── secret ────►  │  Operation  │
└─────────────┘                    └─────────────┘
The entity consuming the secret is deterministic and verifiable.

Agentic Model (3-party):
┌─────────────┐                    ┌─────────────┐                    ┌─────────────┐
│    Human    │ ─── authorizes ──► │    Agent    │ ─── instructs ───► │    Tool     │
│  Principal  │                    │ (decides)   │                    │ (consumes)  │
└─────────────┘                    └─────────────┘                    └─────────────┘
       │                                                                      │
       │                                                                      │
       │           ┌─────────────┐                                            │
       └──────────►│  Guardian   │◄───────────────────────────────────────────┘
            owns   │  (mediates) │   requests secret
                   └─────────────┘
```

The **Human Principal** owns the secrets and authorizes their use. They may not be actively present during agent operation.

The **Agent** decides what operations to perform but must never see secret values. The agent is untrusted with respect to secrets.

The **Tool** performs the actual operation and needs the secret to do so. Tools are semi-trusted: they receive secrets but are scoped to specific profiles.

The **Guardian** mediates all secret access. It enforces authorization, scopes access, and maintains audit trails.

## 4.2 Core Terms

### Agent

An AI system (typically an LLM-based reasoning loop) that autonomously selects and invokes tools to accomplish tasks.

**Key property:** The agent is the *untrusted* party with respect to secrets. Even if the agent becomes aware that a secret exists, the architecture must provide no viable path for the agent to retrieve, reconstruct, or exfiltrate the value. See [Design Principles §5.1](../02-principles/05-design-principles.md#51-principle-of-mediated-access) and [Trust Boundaries §6](../02-principles/06-trust-boundaries.md) for normative requirements.

### Tool

A discrete executable unit (function, server, service, or process) that performs a specific operation on behalf of the agent. Examples include standalone executables, MCP servers, plugin functions, and microservices.

**Key property:** Tools are *semi-trusted executors*. They receive secrets within their authorized scope and perform authenticated operations, but are not trusted beyond that scope. A tool authorized for profile "aws-prod" cannot access "stripe-live" regardless of its behavior. See [Threat Model §3.1](03-threat-model.md#31-threat-actors) for the full trust hierarchy, including the distinction between non-malicious and compromised tools.

### Human Principal

The person who owns the secrets, authorizes their use, and retains ultimate override authority.

**Key property:** The human principal may not be actively present during agent operation.

### Secret

Any piece of information that, alone or in combination, grants access to a resource or enables a privileged capability. This includes credentials, API keys, OAuth tokens, private keys, signing keys, and any other material whose disclosure would permit unauthorized operations.

**Key property:** All secrets are sensitive, but not all sensitive information is a secret. PII, financial data, and medical records are sensitive data governed by other standards. A secret is distinguished by the fact that its disclosure grants *access* or *capability*, not merely information.

### Principal Namespace

A bounded isolation domain within the Guardian that is owned by a single human principal and contains all profiles, tokens, and secrets belonging to that principal.

**Key property:** Profile names are unique within a principal namespace. The same profile name (e.g., `"aws-prod"`) may exist in multiple principal namespaces without collision; they are independent secrets stores with independent access control. A token issued within one principal namespace **MUST NOT** be accepted as authorization for a profile in a different principal namespace, regardless of profile name equality.

**Normative requirements:**

| ID | Level | Requirement |
|----|-------|-------------|
| NS-1 | MUST | Each human principal **MUST** be assigned a distinct principal namespace at provisioning time. Namespace identifiers **MUST** be unique within the Guardian instance and **MUST NOT** be reassigned after a principal is removed |
| NS-2 | MUST | Profile names **MUST** be unique within a principal namespace. The Guardian **MUST** reject attempts to create a profile with a name that already exists within the same namespace |
| NS-3 | MUST | Agent tokens **MUST** be scoped to a specific principal namespace at issuance. The Guardian **MUST** include the principal namespace identifier in the token's canonical signed payload. Tokens **MUST NOT** be honored for profile lookups outside their bound namespace |
| NS-4 | MUST | Cross-namespace access **MUST NOT** be granted implicitly. Any access that spans principal namespaces requires explicit delegation (see [§12](../03-architecture/12-delegation.md)) |

> **Relationship to TS-20:** These requirements directly mitigate [TS-20](03-threat-model.md#32-threat-scenarios) (cross-principal namespace collision). NS-1 ensures namespace identifiers cannot be recycled to impersonate a removed principal's namespace; NS-2 prevents profile name aliasing within a namespace; NS-3 cryptographically binds tokens to their namespace of origin; NS-4 closes the implicit cross-namespace path.

### Secret Profile

A named collection of related secrets and configuration values that share access control policy, owned by a single human principal within their principal namespace. Individual entries within a profile may be requested independently (see [Design Principles §5.2](../02-principles/05-design-principles.md#52-principle-of-minimal-disclosure)), but authorization is granted at the profile level.

**Example:** An "aws-production" profile containing:
- `access_key_id`
- `secret_access_key`
- `region`

**Key property:** Profiles are the atomic unit of access control. Tokens are scoped to profiles, not individual secrets. Profile names are unique within a principal namespace (NS-2).

### Secret Entry

A single key-value pair within a profile, with associated metadata.

**Attributes:**
- `key`: Unique identifier within the profile
- `value`: The secret value (encrypted at rest; see [Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md) for algorithm and key management specifications)
- `sensitive`: Boolean indicating display/logging behavior
- `description`: Human-readable description (optional)
- `field_type`: Hint for UI rendering (optional). This is an open extension point; recommended values are provided in [Annex A](../07-annexes/annex-a-protocol-details.md)

### Guardian Service

A process-isolated mediator that:
- Holds all encryption key material (see [Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md) for key management architecture)
- Enforces access control via token verification
- Mediates human approval when required by profile policy
- Provides secret values exclusively to authorized tools
- Maintains append-only audit logs

**Key property:** The Guardian is the *trusted intermediary* in the three-party model.

### Sensitivity Classification

A per-entry boolean attribute indicating whether the value must be protected from casual exposure.

**Behavior:**
- `sensitive=true`: Masked in UIs, excluded from audit log values
- `sensitive=false`: May be displayed, optionally included in logs

**Important:** All entries are encrypted at rest regardless of sensitivity. Sensitivity affects *display and logging*, not storage security.

## 4.3 Access Control Terms

### Agent Token

A credential scoped to a single profile, presented by the tool in every request to the Guardian to prove authorization.

This version of the standard specifies bearer tokens as the concrete credential type. The access control model is designed to accommodate future credential types, including identity-bound credentials such as agent-attestation certificates or signed identity assertions, without changes to the three-party model or the agent-untrusted invariant. If agentic identity standards mature (see [Scope §2.2](02-scope.md#22-out-of-scope)), the token concept may be extended to bind authorization to a verified agent identity, enabling the Guardian to verify *which agent* is requesting access in addition to *which profile* is being accessed. Such an extension would strengthen accountability and narrow the attack surface for tool substitution ([TS-15](03-threat-model.md#32-threat-scenarios)) but would not change the fundamental property that the agent never receives secret values.

**Properties:**
- Scoped to exactly one profile
- May have an expiration (TTL): see [Conformance §13.3](../04-conformance/13-conformance.md#133-level-2-standard) for TTL requirements by conformance level
- No default expiration: tokens without an explicit TTL remain valid until revoked. Implementations **MUST** require explicit operator acknowledgment when creating a token without a TTL. **At Level 1,** this acknowledgment **MUST** be recorded as a named configuration entry in the Guardian's configuration file or equivalent persistent configuration store. The entry **MUST** identify: (a) the profile name the token is bound to, (b) the token identifier (or a stable reference), (c) the reason no TTL was set, and (d) the date of the acknowledgment. This record **MUST** be machine-readable (e.g., a structured key-value entry, TOML field, or JSON property) so that automated tooling and auditors can verify its presence. **At Level 2 and above,** the Guardian **MUST** record the acknowledgment in the audit log as a lifecycle event with the same four fields. See [Conformance §13.2](../04-conformance/13-conformance.md#132-level-1-basic) for conformance-level TTL requirements.
- Revocable at any time: Token revocation **MUST** take effect for all requests received by the Guardian after the revocation timestamp. In-progress request handling that began (Guardian started processing) before the revocation timestamp **MAY** complete; the Guardian **MUST** log any request completed within 30 seconds after the revocation timestamp at WARN level. The Guardian **MUST NOT** honor any request received after the revocation timestamp, regardless of in-flight state.

### Token Scoping

Each token authorizes access to exactly one profile. A tool holding a token for profile "aws-prod" cannot use it to access profile "stripe-live".

This is the primary secret scoping mechanism. The one-token-one-profile invariant holds regardless of the underlying credential type.

## 4.4 Approval Terms

### Approval Policy

A per-profile configuration governing how secret access is authorized at runtime.

**Modes:**
- `auto`: Access granted on valid token alone
- `prompt_once`: Human confirms once, cached for session TTL
- `prompt_always`: Every access requires explicit human confirmation

### Approval Integrity

The property that the human principal can verify their approval is being delivered to the real Guardian, not to a spoofed dialog or impersonating process.

**Threat:** A malicious process displays a fake approval dialog to capture the human's consent and relay or misuse it ([TS-9](03-threat-model.md#32-threat-scenarios)). The approval mechanism must provide a way for the human to distinguish a genuine Guardian-originated approval request from a forgery.

**Required property:** The approval channel **MUST** provide mutual assurance: the human can verify the approval request originates from the Guardian, and the Guardian can verify the approval response originates from the human. The mechanism used to achieve this varies by environment:

| Environment | Mechanism | Anti-Spoofing Property |
|-------------|-----------|----------------------|
| Interactive (desktop) | Agent-independent channel: native OS dialog, trusted communication platform (Slack, Teams, PagerDuty with authenticated callbacks), or MFA-gated web dashboard, optionally with a Guardian-generated verification code that the human cross-checks against the requesting tool's display | The agent cannot intercept, forge, or dismiss the approval interaction; the channel itself is authenticated, and verification codes (when used) confirm the dialog and the request share a Guardian-authenticated origin |
| Interactive (terminal) | Terminal-based prompt on a stream the agent process cannot access | The agent has no access to the approval terminal's input stream (see [Conformance §13.2](../04-conformance/13-conformance.md#132-level-1-basic)) |
| Headless (CI/CD, server) | Out-of-band approval via authenticated webhook, chat integration, or equivalent channel | The channel itself is authenticated (TLS, HMAC-signed payloads, or equivalent); the agent has no access to the approval channel's credentials |

**Verification codes** are one concrete mechanism for interactive environments. When used, they **MUST** be generated from a cryptographically secure random source and **MUST** be unique within the preceding 24-hour window (Guardian implementations **MUST** maintain a short-term issued-code record for at least 24 hours to enforce this uniqueness guarantee). The 24-hour window, combined with the 48-bit entropy requirement and the single-use invalidation requirement, bounds pre-computation attacks to a manageable search space. Implementations **MUST** produce a code of at least 48 bits of entropy. The recommended format is a group of 3–4 uppercase alphanumeric segments separated by hyphens (e.g., `X7KP-3RMQ-4NST`). Each code **MUST** be single-use: the Guardian **MUST** invalidate it immediately upon approval or denial, or upon expiry of the pending request timeout, whichever occurs first. The Guardian **MUST** enforce a maximum of 3 failed verification code attempts per pending approval request; upon exceeding this limit the Guardian **MUST** deny the pending request and generate a WARN-level audit entry. Code comparisons **MUST** use a constant-time comparison function to prevent timing oracle attacks. The verification code **MUST** be delivered to the human principal through a channel the agent process cannot access. Delivery through tool stdout, agent conversation turns, or any stream the agent process can read is **NOT** conformant under any circumstances, including single-terminal deployments. Implementations that cannot guarantee a separate delivery channel **MUST** use a different anti-spoofing mechanism (e.g., a native OS dialog rendered by the Guardian at the OS privilege boundary, a biometric-gated system approval prompt, or an MFA-gated approval channel) rather than degrading to an agent-observable verification code delivery path.

> **Design note:** The standard does not mandate a single anti-spoofing mechanism because no single mechanism works across all deployment environments. What the standard *does* mandate is the property: the human must be able to verify the authenticity of the approval request, and the agent must have no viable path to forge, intercept, or influence that verification. Implementations must satisfy this property through a mechanism appropriate to their environment.

### Session

A bounded period of cached authorization for specific entries within a profile. A session begins when the human principal approves an access request for specific entries in a profile configured with `prompt_once`, and ends when any of the following occurs, whichever is first:

- The configured TTL expires
- The Guardian process restarts
- The human principal explicitly revokes the cached approval

The session caches approval for the entries shown in the approval dialog. Requests for entries not in the approved set trigger a new approval prompt showing only the new entries; upon approval, the session's approved entry set is expanded without resetting the TTL.

**Session entry expansion constraints:** Entry expansion approval dialogs **MUST** clearly indicate that they are expanding an existing session and **MUST** display the cumulative list of all entries currently approved within the session alongside the new entries being requested. This prevents incremental secret harvesting through a sequence of individually-small expansion requests that aggregate to unauthorized broad access (see [TS-11](03-threat-model.md#32-threat-scenarios)). The human principal **MAY** revoke individual entry approvals within a session without revoking the entire session.

The session TTL is configured per-profile. Cached approval decisions are held in Guardian memory only and **MUST NOT** be persisted to disk.

## 4.5 Lifecycle Terms

### Write-Through

A write operation where the new value is first committed to persistent storage via the Guardian, then the local cache is updated. If the Guardian write fails, the local cache is not modified.

### Write Mode

A per-profile policy governing whether tools may write updated values back through the Guardian.

**Modes:**
- `same`: Evaluates writes using the profile's current read approval policy at the time of each write request. Changes to the read approval policy automatically apply to writes when write mode is `same`
- `auto`: Writes always allowed (for OAuth refresh, etc.)
- `deny`: Profile is read-only
- `prompt_always`: Every write requires human confirmation

### Sensitivity Preservation

When a tool writes a new value for an existing entry without specifying a sensitivity flag, the Guardian preserves the existing entry's sensitivity classification.

**Purpose:** Tools can update tokens without needing to understand the profile's classification scheme.

## 4.6 Delegation Terms

### Delegation Token

A token that authorizes one agent to access specific profiles on behalf of another agent. Does not contain secret values, only authorization to request them from the Guardian.

### Delegation Chain

The sequence of authorizations from the human principal through one or more agents to a final tool. Each link in the chain must be independently auditable. Each link **MUST** attenuate, never amplify, the scope of the preceding link. The delegation chain depth should be bounded in practice; at Level 3, implementations **MUST** enforce a configurable maximum (DEL-9, §12.2). See §12.2 for the level-specific normative requirements. See [TS-12, TS-13, TS-14](03-threat-model.md#32-threat-scenarios) for the threat scenarios that motivate these constraints.

---

Next: [Design Principles](../02-principles/05-design-principles.md)
