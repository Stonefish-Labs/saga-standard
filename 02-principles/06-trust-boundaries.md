# 6. Trust Boundaries and Process Isolation

The three security boundaries defined in the threat model are the architectural foundation of this standard. This section specifies the requirements for each boundary.

## 6.1 Boundary 1: Process Isolation (Agent / Guardian)

The agent reasoning loop and the Guardian service MUST execute in separate OS processes with separate address spaces.

### Architecture

```
+----------------+     +------------------+     +------------------+
|   Agent        |     |  Tool / Skill    |     |   Guardian       |
|  (LLM Loop)   |     |  (Executor)      |     |   Service        |
|                |     |                  |     |                  |
|  - Untrusted   |     |  - Semi-trusted  |     |  - Trusted       |
|  - No secrets  |     |  - Scoped access |     |  - Master key    |
|  - Plans &     |     |  - Short-lived   |     |  - Token auth    |
|    orchestrates|     |    secret        |     |  - Approval      |
|                |     |    value         |     |    mediator      |
+-------+--------+     +--------+---------+     +--------+---------+
        |                        |                        |
        | Invokes tool           | Secret request         |
        | (no secret data)       | (IPC)                  |
        +----------------------->+----------------------->|
                                 |                        |
                                 |<----- Values ----------+
                                 |  (scoped to profile)   |
                                 |                        |
                                 | Authenticated API call |
                                 +----------------------->| External
                                                          | Service
```

### Process Isolation Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| PROC-1 | MUST | Agent and Guardian execute in separate OS processes |
| PROC-2 | MUST | Agent process MUST NOT have read access to secret storage files |
| PROC-3 | MUST | Guardian socket/endpoint MUST enforce token-based authentication on every request, per the token structure ([§9.2](../03-architecture/09-access-control.md#92-token-structure)) and token verification algorithm ([§9.3](../03-architecture/09-access-control.md#93-token-verification)). Specifically: (a) every request MUST include a bearer token in the request header (TOKEN-1); (b) the Guardian MUST verify the HMAC-SHA256 signature of every token on receipt, using the profile-specific signing key (TOKEN-11); (c) the Guardian MUST verify the token has not expired and has not been revoked before granting access (TOKEN-12, TOKEN-13). Transport-layer authentication (mTLS) is a supplementary control (TLS-2) and does not substitute for per-request token verification |
| PROC-4 | SHOULD | Tool processes SHOULD be short-lived or sandboxed |
| PROC-5 | MUST | Master encryption key MUST reside only in Guardian process memory |
| PROC-6 | MUST | Guardian process MUST run with only the OS privileges required for its operation (socket binding, keychain access, file I/O to secret storage). At Level 2 and above, the Guardian **MUST NOT** run as root or with any privilege that grants it memory inspection, process control, or filesystem override authority over other processes. **"Equivalent to root"** is platform-specific and means: on Linux — UID 0 or any process holding dangerous capabilities including CAP_SYS_PTRACE, CAP_DAC_OVERRIDE, CAP_NET_ADMIN, CAP_SYS_ADMIN, or equivalent; on macOS — UID 0, or membership in `wheel` group with sudo access to these capabilities; on Windows — running as SYSTEM, as a member of the Administrators group, or holding SeDebugPrivilege or SeTcbPrivilege. Exception: specific capabilities required for platform keychain access (e.g., `CAP_IPC_LOCK` on some Linux distributions for memory pinning) are permitted when documented in the conformance statement; the Guardian MUST request only the minimum capability set required and MUST document each capability in the conformance statement |
| PROC-7 | MUST | IPC channel permissions MUST restrict access to the owning user |

### Failure Modes

| ID | Level | Requirement |
|----|-------|-------------|
| PROC-8 | MUST | If the Guardian process becomes unavailable or IPC communication fails, all secret access MUST be denied. Tools MUST NOT fall back to cached secrets, direct storage access, or any alternative retrieval mechanism (see [§5.5](05-design-principles.md), Degradation Toward Safety) |
| PROC-9 | MUST | If IPC authentication fails, the Guardian MUST reject the request and log the failure |

### What This Prevents

- **TS-1:** Agent cannot extract secrets from tool output via memory inspection
- **TS-2:** Process isolation is a necessary (but not sufficient) control; the agent cannot directly access tool or Guardian memory to orchestrate exfiltration. Full TS-2 mitigation also requires scoped access (Boundary 2) and approval attestation (Boundary 3)
- **TS-6:** Tool cannot extract encryption keys from Guardian's process memory
- **TS-15:** Combined with token storage isolation, process separation limits the agent's ability to create tools that impersonate legitimate ones by preventing the agent from accessing Guardian-managed token storage directly

### Agent Self-Help Prevention

Process isolation also prevents the agent from bypassing mediation through its own ingenuity. Even if the agent knows a secret exists, separate address spaces and restricted IPC mean the agent cannot:

- Write or execute code that directly reads secret storage
- Intercept tool-to-Guardian communication
- Manipulate tool invocations to redirect secret values into the agent's context

This is a critical property: the barrier is architectural, not behavioral. No amount of prompt engineering, code generation, or tool manipulation by the agent can bridge the process boundary.

---

## 6.2 Boundary 2: Secret Scoping (Tool A / Tool B)

Each tool invocation receives only the secret profile(s) it is authorized to access. A tool authorized for profile "aws-prod" cannot observe, infer, or request profile "stripe-live".

### Token Scoping Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| SCOPE-1 | MUST | Each token MUST be scoped to exactly one profile |
| SCOPE-2 | MUST | Guardian MUST verify token scope matches requested profile on every request |
| SCOPE-3 | MUST | Tokens MUST NOT grant wildcard or cross-profile access |
| SCOPE-4 | SHOULD | Implementations SHOULD support multiple tokens per profile (different agents, different TTLs) |
| SCOPE-5 | MUST | Guardian MUST reject requests with expired, revoked, or malformed tokens. Rejection responses MUST be indistinguishable from scope-mismatch errors to prevent token-state enumeration |
| SCOPE-6 | MUST | Token validation MUST occur on every request. The Guardian MUST NOT cache authorization decisions |

### What This Prevents

- **TS-4:** Compromised tool cannot read secrets from profiles it shouldn't access
- **TS-5:** Malicious tool cannot write poisoned values to another tool's profile
- **TS-18:** Stolen token is scoped to a single profile, limiting the blast radius of token replay

---

## 6.3 Boundary 3: Approval Attestation (System / Human)

The approval mechanism must use a channel that the agent cannot intercept or forge.

### Approval Channel Requirements

> **Terminology:** In the following requirements, "dialog" refers to the approval presentation regardless of channel mechanism: native OS window, messaging service notification (Slack, Teams), web dashboard, webhook callback interface, or any other conformant channel. Requirements apply equally to all channel types.

| ID | Level | Requirement |
|----|-------|-------------|
| DLG-1 | MUST | The approval channel MUST be independent of the agent process; the agent MUST NOT be able to intercept, forge, inject input into, or dismiss the approval interaction. At Level 2 and above, conformant channels include native OS dialogs, authenticated out-of-band services (e.g., Slack, Teams, PagerDuty with authenticated callbacks), MFA-gated web dashboards, and webhook-based approval ([§10.6](../03-architecture/10-approval-policies.md#106-webhook-based-approval)). At Level 1, terminal-based approval is permitted provided the agent process has no access to the approval terminal's input stream (see [Conformance §13.2](../04-conformance/13-conformance.md#132-level-1-basic)). The specific channel mechanism is implementation-defined; conformance is determined by the channel independence property, not the mechanism |
| DLG-2 | MUST | Dialog MUST display the profile name |
| DLG-3 | MUST | Dialog MUST display the token name and partial token ID |
| DLG-4 | MUST | Dialog MUST display the complete list of entry keys being requested without truncation. If the list is long, the dialog MUST use scrolling or pagination, not ellipsis (see [§3.5.2](../01-foundations/03-threat-model.md#352-approval-social-engineering-ts-16), TS-16) |
| DLG-5 | SHOULD | Dialog SHOULD display a verification code to provide anti-spoofing assurance. Verification codes are MUST at Level 3. Deployments that satisfy the anti-spoofing property through alternative mechanisms (MFA-gated approval per-request, authenticated out-of-band channels with per-request confirmation) MAY omit verification codes at Level 2. **Note:** Session-unlock biometrics do NOT qualify as an anti-spoofing equivalent because they attest to identity at session start, not to a human reviewing a specific request at the time it is made; only biometric mechanisms that gate each individual approval action qualify |
| DLG-6 | MUST | When verification codes are displayed, the user **MUST** be able to verify the code by cross-referencing it against the code displayed in the requesting tool's output. The code **MUST** be available in the tool's output before the approval dialog is presented, so the user can verify both before approving |
| DLG-6a | MUST | When the deployment environment allows the agent process to capture tool stdout (the common case in agentic frameworks), verification codes **MUST** be delivered through a channel **the agent process cannot access**. The conformance test is the agent's *capability* to read the channel, not whether the agent currently monitors it — "does not routinely observe" is not sufficient; a channel the agent can access on demand is not a conformant delivery channel. Acceptable channels include: tool stderr (when the agent only captures stdout and has no mechanism to access stderr), a Guardian-provided side-channel outside the agent's OS-level access (e.g., a named pipe or socket accessible only to the tool process by OS permissions), or an out-of-band delivery mechanism that is independent of the agent runtime (SMS, email, authenticator app, hardware token display). Delivery via a stream the agent can access — even if not currently monitored — is **NOT** conformant when an agent-independent channel is available. If no alternative channel is technically feasible, the implementation **MUST** document this limitation in the conformance statement with a description of why agent-independent delivery is not achievable in the deployment environment |
| DLG-7 | MUST | Dialog MUST NOT be dismissable by the agent process |
| DLG-8 | MUST | Dialog default action MUST be "Deny" (no auto-approve on timeout) |
| DLG-9 | SHOULD | Dialog SHOULD have a configurable timeout (default: 60 seconds) |
| DLG-10 | MUST | If the approval channel cannot present the approval interaction to the human principal, access MUST be denied |
| DLG-11 | MUST | Dialog content MUST be generated entirely by the Guardian from its own authoritative records. No text originating from the agent or agent conversation is permitted (see [§3.5.2](../01-foundations/03-threat-model.md#352-approval-social-engineering-ts-16), TS-16) |
| DLG-12 | MUST | Each entry MUST display its sensitivity classification. Entries marked `sensitive=true` MUST be visually distinguished (e.g., icon, color, label) |
| DLG-13 | SHOULD | Dialog SHOULD display a risk-level summary based on profile approval policy and the sensitivity of requested entries |
| DLG-14 | MUST | When a request includes entries not covered by an active `prompt_once` session, the dialog MUST show only the entries requiring new approval. Entries already in the session's approved set MUST NOT be re-prompted. The dialog SHOULD indicate that additional entries from the same profile were previously approved in the current session (see [§10.3 SESS-7](../03-architecture/10-approval-policies.md#103-session-approval-cache)) |
| DLG-15 | MUST | **Approval-path integrity:** The agent process **MUST NOT** have any OS-level capability to read from, write to, inject content into, suppress, or dismiss the approval interaction, regardless of whether the agent and the approval UI execute on the same machine. The conformance test is the agent's *capability* to tamper with the approval channel, not the deployment topology. A single-machine deployment **IS** conformant when the Guardian spawns the approval interaction through a mechanism the agent process cannot access: for example, a native OS window owned by the Guardian process under a separate OS window handle, a terminal session isolated by OS user credentials, or an out-of-band channel on a device the agent cannot reach. A deployment **IS NOT** conformant if the agent process holds any IPC handle, shared file descriptor, or OS primitive by which it could read the verification code, inject approval input, or suppress display of the approval interaction. Implementations **MUST** document in their conformance statement the specific mechanism that prevents agent process access to the approval channel |

### Verification Code Design

Verification codes are one mechanism for satisfying the anti-spoofing property of Boundary 3 (see [§4.4, Approval Integrity](../01-foundations/04-core-concepts.md#44-approval-terms)). They are most valuable in desktop environments where other anti-spoofing controls (MFA, authenticated out-of-band channels) are not available. In environments where the approval channel is already authenticated through stronger mechanisms, verification codes add friction without adding security.

When implemented, the verification code prevents spoofing attacks where a malicious process displays a fake approval dialog:

```
┌─────────────────────────────────────────────┐
│  Secret Access Request                      │
│                                             │
│  Profile: production-db                     │
│  Token:   deploy-bot (a1b2c3d4)             │
│  Policy:  prompt_always                     │
│                                             │
│  Entries requested (2 of 3 sensitive):      │
│    db_host                                  │
│    db_user           🔒 sensitive            │
│    db_password       🔒 sensitive            │
│                                             │
│  Verification Code: XKCD-7291               │  ◄── Generated by Guardian
│                                             │
│  ⚠ All dialog content is Guardian-          │
│    authoritative. Verify this matches       │
│    your intended operation.                 │
│                                             │
│  [ Deny ]                    [ Approve ]    │
└─────────────────────────────────────────────┘
```

The tool's terminal output displays the same code:

```
$ deploy-tool run
Requesting access to profile: production-db
Verification code: XKCD-7291   ◄── User verifies match
Awaiting approval...
```

**Properties (when implemented):**
- Generated by the Guardian, not the requesting process
- Displayed in both the dialog and the requesting tool's terminal
- MUST be generated from a cryptographically secure random source and MUST be unique within the scope of a Guardian session (see [§4.4](../01-foundations/04-core-concepts.md#44-approval-terms))
- Valid only for the duration of the associated approval dialog

> **Implementation note:** The verification code is one anti-spoofing mechanism. The standard mandates the *property* (the agent cannot forge, intercept, or influence the approval verification), not the *mechanism*. Deployments where the approval channel itself is authenticated (e.g., MFA-gated dashboards, HMAC-signed webhooks, biometric-locked desktop sessions) already satisfy this property. In such deployments, verification codes are redundant overhead. The standard recommends verification codes for desktop environments lacking these controls, and requires them at Level 3 as defense-in-depth.

> **Relay attack consideration:** If verification codes are implemented, be aware that the agent typically captures the tool's terminal output and could learn the verification code. The anti-spoofing property then depends on the agent being unable to spawn native OS dialogs. On platforms where this cannot be enforced, implementations SHOULD display the verification code through a channel the agent does not observe (e.g., direct stderr if the agent only captures stdout, or a Guardian-provided side-channel).

### What This Prevents

- **TS-3:** Prompt injection cannot bypass approval (agent cannot interact with the approval channel; see DLG-1)
- **TS-9:** Attacker cannot display a convincing fake dialog (verification code won't match when implemented)
- **TS-16:** Dialog content is Guardian-authoritative, preventing agent-influenced social engineering (DLG-11, DLG-4, DLG-12)
- **TS-17:** Rate limiting and escalating scrutiny controls resist approval fatigue exploitation (see [§3.5.3](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17))

---

## 6.4 Transport Security

The standard is transport-agnostic. Implementations MUST support at least one transport and SHOULD support URL-based selection via a configuration environment variable. Clients MUST NOT fall back to a less-secure transport if the configured transport is unavailable. If the configured transport cannot be established, the client MUST fail with an error, not silently downgrade.

### Unix Domain Sockets (`unix://`)

The RECOMMENDED transport for single-machine deployments.

| ID | Level | Requirement |
|----|-------|-------------|
| UDS-1 | MUST | Socket file permissions MUST be `0600` (owner read/write only) |
| UDS-2 | MUST | Socket file MUST be in a directory with permissions `0700` |
| UDS-3 | MUST | Guardian MUST verify that the connecting process is owned by the same user as the socket owner, using platform-appropriate peer credential mechanisms (e.g., `SO_PEERCRED` on Linux, `LOCAL_PEERCRED` on macOS) |
| UDS-4 | MUST | PID files MUST be maintained for lifecycle management |
| UDS-5 | SHOULD | Default socket path SHOULD be within a user-owned dot-directory under `$HOME` for per-user deployments (e.g., `~/.<implementation>/guardian.sock`), or within a system-level runtime directory (e.g., `/run/<implementation>/`) for system-wide deployments. The chosen directory MUST satisfy the permissions requirements of UDS-1 and UDS-2 |

### TCP (`tcp://`)

For development and loopback-only deployments.

| ID | Level | Requirement |
|----|-------|-------------|
| TCP-1 | MUST | TCP binding MUST be to loopback (`127.0.0.1` or `::1`) unless TLS is used |
| TCP-2 | SHOULD | Warning SHOULD be issued for non-loopback without TLS |
| TCP-3 | MUST | Token-based authentication MUST be enforced |

### TLS (`tls://`)

REQUIRED for multi-machine and production remote deployments.

| ID | Level | Requirement |
|----|-------|-------------|
| TLS-1 | MUST | TLS 1.3 or later |
| TLS-2 | MUST/SHOULD | Mutual TLS (mTLS) for caller authentication. **At Level 2 and Level 3, mTLS is MUST** for all Guardian communication over TCP/TLS transports — the TS-18 (token theft and replay) threat is modeled as a realistic risk at Level 2 and above, and mTLS provides cryptographic caller authentication that token-based authentication alone cannot supply against an on-path adversary (see [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios)). At Level 3, see also CONF-L3-8. **At Level 1, mTLS is SHOULD** — strongly recommended but not required as a hard conformance gate. Level 1 deployments that do not implement mTLS MUST document the decision in their conformance statement and MUST ensure that token-based authentication (PROC-3, §9.3) provides the primary caller authentication mechanism |
| TLS-3 | MUST | Token-based authentication in addition to transport |
| TLS-4 | MUST | Server certificates MUST be validated. Certificates MUST be validated against a trusted certificate authority (CA). Self-signed certificates MUST NOT be trusted implicitly. Exception: private deployments operating within a dedicated internal PKI (e.g., an organization-managed internal CA, HashiCorp Vault PKI, or equivalent) MAY use certificates signed by that internal CA, provided: (a) the internal CA's root certificate is explicitly configured as a trusted anchor in the Guardian and all clients; (b) the CA is operated exclusively by the deploying organization; and (c) the CA configuration is documented in the conformance statement. Ad-hoc or auto-generated self-signed certificates with no PKI chain are **NOT** conformant. |
| TLS-5 | SHOULD | CA certificate path configurable |

---

## 6.5 Package Separation

Implementations MUST maintain strict separation between client-side code (used by agents and tools) and server-side code (Guardian, vault engine, CLI).

| ID | Level | Requirement |
|----|-------|-------------|
| PKG-1 | MUST | Client library MUST NOT include server-side code |
| PKG-2 | MUST | Client library MUST be installable independently with minimal dependencies |
| PKG-3 | MAY | Server package MAY depend on the client package for shared type definitions, but MUST NOT depend on client code for runtime functionality |
| PKG-4 | MUST | Client-only install MUST NOT bypass Guardian |
| PKG-5 | SHOULD | Client library SHOULD be vendorable as a single file |
| PKG-6 | SHOULD | Client SHOULD auto-start Guardian only for local transports |

### Rationale

The primary threat is an agent (or compromised tool) using server-side code to bypass the Guardian's authentication, approval, and audit controls. If a tool has access to the vault engine and master key derivation code, it could decrypt secrets directly.

---

Next: [Autonomy Tiers](07-autonomy-tiers.md)
