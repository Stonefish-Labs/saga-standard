# 5. Design Principles

This standard is built on six non-negotiable design principles. These principles are the foundation for every architectural decision in the standard. If you're evaluating whether a system is compliant, start here.

## 5.1 Principle of Mediated Access

> **Secrets MUST be accessed exclusively through a mediated channel. No tool, agent, or process shall access secret storage directly.**

The Guardian service (or equivalent mediator) is the sole entity that holds the master encryption key and decrypts secret values. All consumers access secrets through a request-response protocol to the Guardian. There is no "direct mode" or "bypass" for performance.

### Why This Matters

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

Compromise outside these assumptions is addressed as accepted risk in [Threat Model §3.4](../part-1-foundations/03-threat-model.md#34-accepted-risks).

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
- By default, secret values MUST be retained only for the active operation scope and MUST be cleared from process memory buffers immediately after use where the runtime permits deterministic clearing
- Implementations MAY cache retrieved secret entries in memory for the duration of an explicitly human-approved session (for example, `prompt_once` with a configured TTL). Such cache MUST be scoped to requested entries and MUST be discarded when the session ends, the TTL expires, or the human principal revokes access -- whichever comes first (aligned with TOPO-6 in [Threat Model §3.6](../part-1-foundations/03-threat-model.md#36-guardian-deployment-topology))
- Implementations MUST NOT persist secret values to disk-backed logs, crash reports, or diagnostic traces
- Tool responses, logs, and agent-visible output channels MUST NOT include raw secret values unless explicitly authorized by a human-approved break-glass workflow

### Why This Matters

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

> **Every secret entry MUST carry an explicit sensitivity classification. The classification MUST be set by the human principal, not inferred by the system.**

### Behavior

| Behavior | `sensitive=true` | `sensitive=false` |
|----------|-----------------|-------------------|
| Encryption at rest | Required | Required |
| Display in CLI/UI | Masked (****) | Shown |
| Included in audit log values | No | Optional |
| Default for new entries | Yes | No |

### Critical Requirement

**All entries MUST be encrypted at rest regardless of sensitivity classification.** Sensitivity affects *display and logging behavior*, not storage security. An implementation that stores non-sensitive entries in plaintext is non-conformant. See [Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md) for algorithm and key management requirements.

### Why This Matters

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

Authorization failures and profile-resolution failures SHOULD return indistinguishable responses to unauthorized callers to reduce profile-enumeration risk.

**If any step fails, a local cache (if present) MUST NOT be updated.**

### Why This Matters

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

### Why This Matters

In security systems, the safe default is denial. Convenience features that default to allowing access when authorization cannot be verified are attack vectors.

> **If in doubt, deny.**

---

## 5.6 Principle of Human Supremacy

> **The human principal retains final authority over secret access decisions. No system component, agent behavior, or automation policy may override an explicit human denial or revocation.**

### Conformance Properties

- Revocation of a token, entry, or profile MUST take effect on the next request
- An explicit human denial MUST terminate the pending access attempt
- The human principal MUST be able to force re-approval regardless of session cache state
- The system MUST provide human-readable audit visibility for all secret access attempts

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

### Why This Matters

The human owns the secrets and the consequences that those secrets create. This is not a technical property--it's a governance principle. The architecture exists to serve the human's intent, not to substitute for it.

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
