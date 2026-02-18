# 5. Design Principles

This standard is built on six non-negotiable design principles. These principles are the foundation for every architectural decision in the standard. If you're evaluating whether a system is compliant, start here.

## 5.1 Principle of Mediated Access

> **All access to secrets MUST be mediated through the Guardian. Tools, agents, and all other processes MUST NOT access secret storage directly.**

Secret storage (the encrypted store and the master decryption key) **MUST** be accessible only to the Guardian process. All other processes **MUST NOT** access secret storage directly by any mechanism — including direct file access, shared memory, environment variable injection, or any out-of-band path that circumvents the mediation protocol. There is no "direct mode" or performance bypass.

The Guardian service (or equivalent mediator) is the sole entity that holds the master encryption key and decrypts secret values. All consumers access secrets through a request-response protocol to the Guardian. There is no "direct mode" or "bypass" for performance.

### Rationale

Direct access makes access control and auditing impossible to enforce consistently. Without a mediation point:

- There's no single place to verify authorization
- There's no consistent way to log access
- There's no way to enforce approval policies
- Compromise of any component means compromise of all secrets

With mediation:

- Every access passes through a single enforcement point
- Token verification, approval policies, write restrictions, and audit logging are uniformly applied
- Compromise is contained to authorized profiles
- Under the standard trust assumptions (trusted kernel, uncompromised tool process, authenticated mediator channel), the agent has no viable architectural path to retrieve secret values directly

Compromise outside these assumptions is addressed as accepted risk in [Threat Model §3.4](../01-foundations/03-threat-model.md#34-accepted-risks).

### What This Looks Like

```
WRONG:
┌─────────────┐     direct file access     ┌─────────────┐
│    Tool     │ ─────────────────────────► │ Secret File │
└─────────────┘                            └─────────────┘

RIGHT:
┌─────────────┐     mediated request      ┌─────────────┐     decrypt      ┌─────────────┐
│    Tool     │ ────────────────────────► │  Guardian   │ ───────────────► │ Secret File │
└─────────────┘                           └─────────────┘                  └─────────────┘
```

---

## 5.2 Principle of Minimal Disclosure

> **A tool MUST receive only the secret entries it needs, and only at the time it needs them.**

### Requirements

- Implementations MUST support per-key access within a profile (requesting one or more explicit entries rather than the full profile by default)
- Implementations MUST NOT pre-populate tool environments with secrets speculatively
- Tools MUST request only the keys required for the active operation
- By default, secret values MUST be retained only for the active operation scope and MUST be cleared from process memory buffers immediately after use where the runtime permits deterministic clearing. In runtimes with garbage collection or managed memory (Python, JavaScript/Node.js, Java, Go, Ruby, and similar), deterministic clearing is not guaranteed; in these environments implementations MUST use the runtime's most secure available mechanism (e.g., explicit zeroing via `ctypes` or native FFI in Python, typed array fill in JavaScript, explicit byte array zeroing in Java, or equivalent) and MUST document in the conformance statement whether deterministic clearing is achievable in the target runtime. The goal of this requirement is to reduce the window of memory exposure, acknowledging that it cannot be absolute in all runtimes
- Implementations MAY cache retrieved secret entries in memory for the duration of an explicitly human-approved session (for example, `prompt_once` with a configured TTL). Such cache MUST be scoped to requested entries and MUST be discarded when the session ends, the TTL expires, or the human principal revokes access, whichever comes first (aligned with TOPO-6 in [Threat Model §3.6](../01-foundations/03-threat-model.md#36-guardian-deployment-topology))
- Implementations MUST NOT persist secret values to disk-backed logs, crash reports, or diagnostic traces
- Tool responses, logs, and agent-visible output channels MUST NOT include raw secret values unless explicitly authorized by a human-approved break-glass workflow

### Rationale

Minimizing the temporal and spatial exposure of secrets:

- Reduces the window of opportunity for exfiltration
- Limits the impact of tool compromise
- Makes audit trails more precise

### What This Looks Like

```
WRONG:
Tool loads a full profile at startup and keeps it resident for the entire run regardless of what keys are actually needed

RIGHT:
Tool requests only the specific key immediately before use. If a human-approved session cache is active, only requested keys are kept in memory until session end/TTL/revocation, then discarded
```

---

## 5.3 Principle of Declared Sensitivity

> **Every secret entry MUST carry an explicit sensitivity classification. The classification value present in the stored entry MUST reflect the last explicit setting by the human principal. Conformant implementations MUST NOT automatically change a classification value based on the entry's key name, value content, or any heuristic without an explicit human action.**

### Behavior

| Behavior | `sensitive=true` | `sensitive=false` |
|----------|-----------------|-------------------|
| Encryption at rest | Required | Required |
| Display in CLI/UI | Masked (****) | Shown |
| Included in audit log values | No | Optional |
| Default for new entries | Yes | No |

### Critical Requirements

**All entries MUST be encrypted at rest regardless of sensitivity classification.** Sensitivity affects *display and logging behavior*, not storage security. An implementation that stores non-sensitive entries in plaintext is non-conformant. See [Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md) for algorithm and key management requirements.

**Testable behavioral requirement:** Conformance for the "set by human principal" property is verified by the following observable test: (1) create an entry programmatically via the Guardian's administrative API without specifying a sensitivity value — the entry MUST receive the default value (`sensitive=true` per the default column above), not a value inferred from the key name; (2) provide a key whose name contains the string "password" or "secret" with an explicit `sensitive=false` flag — the Guardian MUST accept and store `sensitive=false` without override. A system that overrides a human-specified `sensitive=false` based on key name heuristics is non-conformant.

### Rationale

The system must not auto-classify because risk tolerance varies by context:

- An endpoint URL may be sensitive in one deployment and public in another
- A region identifier might reveal infrastructure topology
- What's "just configuration" to one organization is "sensitive metadata" to another

The human principal owns the classification decision.

---

## 5.4 Principle of Write-Through Integrity

> **Secret writes MUST pass through the same mediation channel as reads. There is no separate write path.**

### Write-Through Protocol

1. Tool sends write request to Guardian with profile, key, and value
2. Guardian verifies token authenticity and revocation status
3. Guardian verifies token scope authorizes the requested profile
4. Guardian evaluates write approval policy
5. If approved: Guardian validates profile and entry constraints
6. Guardian encrypts and persists
7. Guardian logs the write with audit context
8. Guardian returns success
9. If a local cache exists, the tool updates local cache

| ID | Level | Requirement |
|----|-------|-------------|
| WTI-1 | MUST | Authorization failures and profile-resolution failures **MUST** return indistinguishable responses to unauthorized callers. The response body, HTTP status code (for HTTP transports), and error code **MUST** be identical for "profile not found" and "profile found but access denied." Profile enumeration — mapping which profile names exist by observing the distinction between these two error conditions — is the first step of reconnaissance against any secrets management system and **MUST** be prevented by design |
| WTI-2 | MUST | Implementations **MUST** apply a random response delay to all rejection responses to prevent timing-based profile discrimination. The delay **MUST** be uniformly sampled from a configurable window (default: minimum 20ms, maximum 200ms). The delay **MUST** be applied after the full authorization evaluation so that the timing profile of rejection is independent of whether the profile exists |

**If any step fails, a local cache (if present) MUST NOT be updated.**

### Rationale

Separate write paths create vulnerabilities:

- TOCTOU (time-of-check/time-of-use) attacks
- Audit gaps where writes aren't logged
- Policy bypass where write restrictions aren't enforced

A single channel ensures all modifications are logged and policy-checked.

---

## 5.5 Principle of Degradation Toward Safety

> **When the system cannot determine authorization, it MUST deny access. When a component fails, the failure mode MUST prevent secret exposure, not permit it.**

### Fail-Closed Behavior

| Condition | Required Behavior |
|-----------|-------------------|
| Guardian unreachable | Deny access (no fallback to direct storage) |
| Approval dialog cannot display | Deny access |
| Token cannot be verified | Deny access |
| Write mode unrecognized | Deny write |
| Profile not found | Return error, do not expose other profiles |

### Rationale

In security systems, the safe default is denial. Convenience features that default to allowing access when authorization cannot be verified are attack vectors.

> **If in doubt, deny.**

---

## 5.6 Principle of Human Supremacy

> **The human principal retains final authority over secret access decisions. No system component, agent behavior, or automation policy may override an explicit human denial or revocation.**

### Conformance Properties

| ID | Level | Requirement |
|----|-------|-------------|
| SUPR-1 | MUST | Revocation of a token, entry, or profile **MUST** take effect for all requests received by the Guardian after the revocation timestamp. The Guardian **MUST NOT** honor any request received after the revocation timestamp, regardless of in-flight state |
| SUPR-2 | MUST | An explicit human denial **MUST** terminate the pending access attempt |
| SUPR-3 | MUST | The human principal **MUST** be able to force re-approval for any profile regardless of session cache state |
| SUPR-4 | MUST | The system **MUST** provide human-readable audit visibility for all secret access attempts |
| SUPR-5 | MUST | In multi-Guardian deployments (horizontally scaled Guardians sharing a common storage backend or operating in a cluster), revocation **MUST** be propagated to all active Guardian instances within a configurable propagation window (default: not to exceed 5 seconds). Guardian instances **MUST NOT** honor requests for revoked tokens beyond this propagation window. The propagation mechanism (database polling, pub/sub notification, or equivalent) **MUST** be documented in the conformance statement. Where the propagation window cannot be guaranteed (e.g., network partition between Guardian instances), the Guardian **MUST** fail closed: deny all requests until revocation state can be verified |

### Rights the Human Always Retains

The human principal can always:

- Revoke any profile, entry, or token immediately
- Force re-approval for any profile regardless of session cache
- Deny any pending approval request
- Inspect the complete audit log
- Disable any agent's access

### What This Prohibits

No automation tier, session approval cache, or convenience feature may:

- Prevent the human from exercising these capabilities
- Create a situation where revocation requires waiting
- Allow an agent to escalate its own permissions
- Bypass human authority for "efficiency"

### Rationale

The human owns the secrets and the consequences that those secrets create. This is a governance principle, not a technical property. The architecture exists to serve the human's intent, not to substitute for it.

Automation is delegation, not abdication.

---

## Summary

| Principle | Core Requirement | Prevents |
|-----------|-----------------|----------|
| Mediated Access | All access through Guardian | Bypass attacks, inconsistent enforcement |
| Minimal Disclosure | Only what's needed, when needed | Broad exposure, exfiltration |
| Declared Sensitivity | Human-classified entries | Auto-classification errors, over/under-protection |
| Write-Through Integrity | Single channel for reads and writes | TOCTOU, audit gaps, policy bypass |
| Degradation Toward Safety | Fail closed, never fail open | Default-allow vulnerabilities |
| Human Supremacy | Human retains final authority | Authority erosion, non-revocable access |

---

Next: [Trust Boundaries](06-trust-boundaries.md)
