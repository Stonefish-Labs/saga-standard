# Appendix A: Evaluation Criteria (Informative)

> **Note:** This appendix is informative. It does not contain normative requirements. It provides a practical framework for evaluating whether an agentic system adequately protects secrets. Use it when assessing a vendor's claims, reviewing an internal implementation, or conducting a security audit.

## How to Use This Guide

Each criterion has:
- **The question to ask** -- What you're trying to determine
- **What good looks like** -- Indicators of proper implementation
- **Red flags** -- Warning signs that warrant deeper investigation
- **Why it matters** -- The risk if this control is missing

## A.1 Process Isolation

### Q1: Where does the master encryption key live at runtime?

**What to look for:**
- Key exists only in a dedicated Guardian/mediator process
- Key is derived from OS keychain or hardware security module
- Key is never written to disk, environment variables, or config files

**Red flags:**
- Key stored in a config file (even encrypted)
- Key passed via environment variable
- Key accessible to the agent process
- "We encrypt it with a key stored in..." (just moves the problem)

**Why it matters:** If the agent or any tool can access the master key, they can decrypt all secrets. The entire security model collapses.

---

### Q2: Does the agent run in the same process as the secret store?

**What to look for:**
- Agent and Guardian are separate OS processes
- No shared memory between agent and Guardian
- Communication via IPC (sockets, not direct function calls)

**Red flags:**
- "It's all in one service for simplicity"
- Agent imports the secret library directly
- No process boundary documentation

**Why it matters:** Same process = same memory space. A compromised agent or tool can read the Guardian's memory, including decrypted secrets and the master key.

---

### Q3: Can the agent directly access secret storage files?

**What to look for:**
- Storage files owned by Guardian process user only
- Agent runs as different user with no read access
- File permissions are `0600` or equivalent

**Red flags:**
- Agent runs as root or same user as Guardian
- "The files are encrypted so it's fine" (encryption without key separation is theater)
- Storage in agent-accessible directories

**Why it matters:** Encrypted files with accessible keys are as good as plaintext. The encryption must be backed by a key the agent cannot access.

---

## A.2 Secret Scoping

### Q4: How are tools limited to specific secrets?

**What to look for:**
- Per-profile tokens (one token = one profile)
- Token verification on every request
- No wildcard or "all profiles" access

**Red flags:**
- Single token for all profiles
- Tools can request any profile by name
- "Trust the tool, it's our code"

**Why it matters:** Without scoping, a compromised tool can access all secrets. Compartmentalization limits blast radius.

---

### Q5: Can a tool access secrets it wasn't explicitly granted?

**What to look for:**
- Explicit token-to-profile mapping
- Guardian rejects requests for unscoped profiles
- Audit log shows which profile each request targeted

**Red flags:**
- Tools can enumerate available profiles
- "The tool knows which profile it needs"
- No server-side scope enforcement

**Why it matters:** The tool shouldn't discover what profiles exist. It should only know about profiles it's been explicitly authorized to access.

---

### Q6: Are secrets shared across tools or environments inappropriately?

**What to look for:**
- Separate profiles for dev/staging/production
- Different tokens for different tools
- No shared "admin" tokens across services

**Red flags:**
- One profile for all environments
- Same token used by multiple tools
- "We just use the production key everywhere"

**Why it matters:** Shared secrets mean shared compromise. When one tool is breached, you want to know exactly which secrets are exposed.

---

## A.3 Approval and Oversight

### Q7: How does the human approve secret access?

**What to look for:**
- Native OS dialogs, not terminal prompts (Level 2+)
- Verification codes that match between dialog and tool output
- Default action is "Deny"
- Dialog content generated entirely by Guardian -- no agent-originated text (DLG-11)
- Complete list of entry keys displayed without truncation (DLG-4)
- Sensitivity classification visible for each entry (DLG-12)

**Red flags:**
- "Just type 'y' in the terminal"
- Agent can read or interact with the approval prompt
- Auto-approve on timeout
- No approval mechanism at all
- Dialog includes a "reason" or "description" field populated by the agent
- Entry list is truncated with ellipsis when many entries are requested
- No visual distinction between sensitive and non-sensitive entries

**Why it matters:** If the agent can interact with the approval mechanism, prompt injection can bypass it (TS-3). If the agent can influence the dialog's content, it can socially engineer the human into approving unintended access (TS-16). The approval channel must be outside agent control *and* display only Guardian-authoritative information.

---

### Q8: Can the user always revoke access?

**What to look for:**
- Immediate revocation (no waiting for TTL)
- Works even during active sessions
- Revokes tokens, not just session cache

**Red flags:**
- "Wait for the session to expire"
- Can only revoke between operations
- No revocation mechanism

**Why it matters:** The human must always be able to say "stop." Any delay in revocation is a window for exfiltration.

---

### Q9: What happens when approval is required but no human is available?

**What to look for:**
- Access denied (fail closed)
- Optional webhook/Slack integration for remote approval
- Clear error message to the tool

**Red flags:**
- Auto-approve after timeout
- Fall back to unauthenticated access
- "Just use auto-approval for headless"

**Why it matters:** Failures should err on the side of security. If you can't get approval, don't grant access.

---

## A.4 Audit and Observability

### Q10: Is every secret access logged?

**What to look for:**
- All reads, writes, and deletes logged
- Log includes: timestamp, profile, token identity, entries accessed
- Approval method recorded (auto, session, interactive)

**Red flags:**
- Only failed accesses logged
- Log doesn't include which entries were accessed
- Log can be modified or deleted

**Why it matters:** In a breach, you need to know exactly what was accessed. Incomplete logs mean incomplete incident response.

---

### Q11: Are secret values in the audit log?

**What to look for:**
- Values NEVER in logs
- Keys logged, values not
- Even non-sensitive entries excluded from log values

**Red flags:**
- "We log everything for debugging"
- Non-sensitive entries logged with values
- Logs stored in agent-accessible location

**Why it matters:** Logs are often less protected than secrets. A log leak shouldn't become a secret leak.

---

### Q12: Can you detect anomalous access patterns?

**What to look for:**
- Alert on unusual access frequency
- Alert on access to high-value profiles
- Alert on access from new tokens or processes

**Red flags:**
- No monitoring on audit logs
- Logs only reviewed after incidents
- No baseline of normal access patterns

**Why it matters:** Without anomaly detection, slow exfiltration can go unnoticed for months.

---

## A.5 Secret Lifecycle

### Q13: How are secrets updated (OAuth refresh, rotation)?

**What to look for:**
- Write-back through same mediated channel as reads
- Same approval policies apply to writes
- Audit log captures write operations

**Red flags:**
- Tools store refreshed tokens in their own storage
- Bypass Guardian for writes "for performance"
- No write audit trail

**Why it matters:** Write-back through a different path creates TOCTOU vulnerabilities and audit gaps.

---

### Q14: What happens if a write operation fails?

**What to look for:**
- Tool's local cache NOT updated on failure
- Clear error to tool
- Retry possible

**Red flags:**
- Tool caches value locally before Guardian confirms
- Silent failure with stale cache
- No write failure handling

**Why it matters:** Local cache should always reflect Guardian state. Divergence creates confusion and potential for using stale credentials.

---

## A.6 Delegation

### Q15: How do secrets flow between agents?

**What to look for:**
- No direct secret passing between agents
- Delegation tokens authorize access, don't contain secrets
- Full delegation chain in audit trail

**Red flags:**
- "Agent A passes the secret to Agent B"
- No delegation tracking
- Unlimited delegation depth

**Why it matters:** Direct passing breaks isolation. Delegation must be tracked to maintain accountability.

---

## A.7 Cryptographic Soundness

### Q16: How are secrets encrypted at rest?

**What to look for:**
- AES-256-GCM or equivalent AEAD
- Unique nonce/IV per entry
- Nonce randomly generated, not sequential

**Red flags:**
- "AES-256-CBC" (not authenticated, vulnerable to padding attacks)
- Same nonce for multiple entries
- Sequential nonces (predictable)

**Why it matters:** Authenticated encryption prevents tampering. Nonce reuse with the same key breaks confidentiality.

---

### Q17: Is the master key derived from a password?

**What to look for:**
- If yes: Argon2id or scrypt with sufficient work factor
- If no: CSPRNG-generated key stored in OS keychain

**Red flags:**
- PBKDF2 with low iteration count
- SHA-256(password) as key
- Key stored in file without additional protection

**Why it matters:** Password-derived keys are only as strong as the password and KDF. Modern KDFs resist brute-force; naive hashing doesn't.

---

## A.8 Agent-Initiated Threats

### Q18: Is the approval dialog content unambiguous and complete?

**What to look for:**
- All dialog content generated by Guardian, not influenced by agent (DLG-11)
- Complete entry list displayed without truncation (DLG-4)
- Sensitivity classification visible per entry (DLG-12)
- Risk-level summary shown (DLG-13)

**Red flags:**
- Dialog includes a "reason" or "context" field populated by the agent
- Long entry lists truncated with "..." or ellipsis
- No visual distinction between sensitive and non-sensitive entries
- Profile names are ambiguous or don't clearly indicate risk level

**Why it matters:** The agent controls the conversational context. If the dialog also contains agent-originated content, the human's decision is based entirely on information the agent can manipulate. Guardian-authoritative dialog content is the last line of defense against approval social engineering (TS-16).

---

### Q19: Can the agent create or substitute tools to intercept secrets?

**What to look for:**
- Tokens stored in locations inaccessible to the agent process
- Tool registration mechanism where Guardian verifies tool identity
- Token delivery through a channel the agent cannot observe
- At Level 3: process attestation (binary hash, code signing)

**Red flags:**
- Tokens stored in environment variables accessible to the agent
- No tool registration -- any process with a valid token can request secrets
- Agent framework passes tokens to tools through its own invocation chain
- Agent has filesystem access to token storage paths

**Why it matters:** Agents with code execution capabilities can write their own tools. If the agent can obtain a valid token and connect to the Guardian, the Guardian has no way to distinguish the agent-authored tool from a legitimate one (TS-15).

---

### Q20: Does the system defend against approval fatigue?

**What to look for:**
- Rate limiting on approval requests
- Escalating confirmation after repeated approvals (PIN, delay, biometric)
- Consolidated view of multiple pending requests
- Audit logging of approval timing and patterns

**Red flags:**
- No limit on approval request frequency
- No distinction between rapid sequential approvals and spaced-out approvals
- No visibility into aggregate request scope across a session
- Rapid approvals (< 2 seconds) not flagged for review

**Why it matters:** Even with perfect dialog content, humans degrade in vigilance over repeated prompts. An agent can exploit this by mixing legitimate low-risk requests with high-risk ones, grinding through human attention with volume (TS-17).

---

## A.9 Evaluation Summary Checklist

| Area | Key Questions |
|------|---------------|
| Process Isolation | Q1-Q3 |
| Secret Scoping | Q4-Q6 |
| Approval & Oversight | Q7-Q9 |
| Audit & Observability | Q10-Q12 |
| Secret Lifecycle | Q13-Q14 |
| Delegation | Q15 |
| Cryptographic Soundness | Q16-Q17 |
| Agent-Initiated Threats | Q18-Q20 |

### Quick Assessment

If you can answer "yes" to all of these, the system has strong secret management:

1. ✓ Master key only in Guardian process memory
2. ✓ Agent and Guardian are separate processes
3. ✓ Agent cannot access storage files
4. ✓ Per-profile tokens with server-side enforcement
5. ✓ Native approval dialogs with verification codes and Guardian-authoritative content
6. ✓ Immediate revocation available
7. ✓ All access logged, values excluded
8. ✓ Anomaly detection on access patterns
9. ✓ Write-back through mediated channel
10. ✓ AEAD encryption with unique nonces
11. ✓ Agent cannot create tools that intercept secrets (token isolation, tool registration)
12. ✓ Approval fatigue controls (rate limiting, escalating confirmation)

If you see red flags in multiple areas, the system likely has fundamental architectural issues that no amount of operational hardening can fix.

---

Next: [Compensating Controls](appendix-b-compensating-controls.md)
