# Appendix B: Compensating Controls (Informative)

> **Note:** This appendix is informative. It does not contain normative requirements. It provides a framework for compensating controls--additional safeguards that reduce risk when the primary control cannot be fully implemented. Not every environment can implement the standard perfectly; legacy systems, organizational constraints, or technical limitations may prevent full architectural isolation.

## What Compensating Controls Are

Compensating controls are alternative measures that provide similar protection when the preferred control is not achievable. They:

- Do not replace the primary control
- Reduce (not eliminate) the risk
- Have their own limitations and costs
- Should be temporary while working toward the ideal

## The Control Effectiveness Hierarchy

Controls vary in effectiveness. When selecting compensating controls, understand where they fall:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MOST EFFECTIVE                               │
│                                                                 │
│  Architectural Controls                                         │
│  (Process isolation, secret scoping, mediated access)           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Technical Controls                                             │
│  (Encryption, network segmentation, rate limiting)              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Operational Controls                                           │
│  (Audit review, rotation policies, monitoring)                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Administrative Controls                                        │
│  (Policies, training, access reviews)                           │
│                                                                 │
│                    LEAST EFFECTIVE                               │
└─────────────────────────────────────────────────────────────────┘
```

Architectural controls are most effective because they cannot be bypassed. Administrative controls are least effective because they depend on human behavior.

**Goal:** Implement architectural controls. When you can't, stack multiple compensating controls from lower tiers.

---

## Control Matrix

This matrix maps risks to available compensating controls.

### Risk: Agent Can Access Secrets Directly

*Primary control not implemented: Process isolation*

| Control | Effectiveness | Cost | Description |
|---------|---------------|------|-------------|
| Short token TTL | Medium | Low | Limit exposure window with 1-4 hour token expiration |
| Credential rotation | Medium | Medium | Rotate credentials frequently (daily/weekly) |
| Read-only credentials | Medium | Low | Use credentials with minimal required permissions |
| Audit monitoring | Low | Medium | Alert on all access within seconds |
| Access review | Low | High | Regular human review of all credential usage |

**Recommended combination:** Short TTL + credential rotation + audit monitoring

### Risk: Tools Not Properly Scoped

*Primary control not implemented: Per-profile tokens*

| Control | Effectiveness | Cost | Description |
|---------|---------------|------|-------------|
| Separate service accounts | Medium | Medium | Each tool uses different cloud service account |
| Permission boundaries | Medium | Low | Cloud provider IAM boundaries limit tool scope |
| Network segmentation | Medium | High | Tools can only reach authorized endpoints |
| Rate limiting | Low | Low | Prevent bulk operations via API limits |
| Usage anomaly detection | Low | Medium | Alert on unusual access patterns |

**Recommended combination:** Separate service accounts + permission boundaries + rate limiting

### Risk: Approval Mechanism Bypassed

*Primary control not implemented: Native dialogs*

| Control | Effectiveness | Cost | Description |
|---------|---------------|------|-------------|
| Time-bounded access | Medium | Low | Pre-approved access windows (e.g., 9am-5pm only) |
| Multi-party approval | Medium | High | Require two humans to approve high-risk access |
| Break-glass logging | Low | Low | Emergency access is logged and reviewed |
| Access justification | Low | Low | Require ticket number for each access |
| Delayed access | Low | Medium | Wait period between request and grant |

**Recommended combination:** Time-bounded access + access justification + audit review

### Risk: No Audit Trail

*Primary control not implemented: Complete logging*

| Control | Effectiveness | Cost | Description |
|---------|---------------|------|-------------|
| Cloud provider logs | Medium | Low | Enable CloudTrail/Audit Logs for all API access |
| Network logging | Low | Medium | Log all outbound connections from agent infrastructure |
| Session recording | Low | High | Record terminal sessions for forensic review |
| Periodic reconciliation | Low | High | Compare credential usage to expected operations |

**Recommended combination:** Cloud provider logs + network logging

### Risk: Secrets Leaked to Agent Context

*Primary control not implemented: Agent isolation*

| Control | Effectiveness | Cost | Description |
|---------|---------------|------|-------------|
| Context not logged | Medium | Low | Ensure agent context is not persisted |
| Short sessions | Medium | Low | Restart agent sessions frequently |
| Credential format detection | Low | Medium | Scan for credential patterns in agent output |
| Post-session rotation | Low | Medium | Rotate credentials after each session |

**Recommended combination:** Context not logged + short sessions + post-session rotation

---

## Detailed Control Descriptions

### Short Token TTL

**What it is:** Tokens expire quickly (1-4 hours), requiring frequent re-authorization.

**How it helps:** Even if a token is compromised, the attacker has a limited window.

**Implementation:**
```bash
# Generate short-lived token
guardian token grant --profile production --ttl 3600  # 1 hour
```

**Limitations:**
- Requires operational process to rotate tokens
- May impact long-running operations
- Doesn't prevent exfiltration within the TTL window

### Credential Rotation

**What it is:** Secrets are rotated on a regular schedule.

**How it helps:** Compromised credentials become stale quickly.

**Implementation:**
- Daily rotation for high-value credentials
- Weekly rotation for medium-value
- Monthly rotation minimum for all credentials

**Limitations:**
- Operational overhead
- Must update all consumers
- Rotation itself is a sensitive operation

### Permission Boundaries

**What it is:** Cloud provider IAM policies limit what credentials can do.

**How it helps:** Even if credentials are compromised, attacker is limited by IAM.

**Implementation:**
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject"],
  "Resource": "arn:aws:s3:::specific-bucket/*"
}
```

**Limitations:**
- Only applies to cloud provider credentials
- Doesn't prevent exfiltration of the credential itself
- Complex IAM can be misconfigured

### Network Segmentation

**What it is:** Tools can only reach authorized network endpoints.

**How it helps:** Limits where exfiltrated credentials can be sent.

**Implementation:**
- VPC with restricted egress
- Allow-list for external endpoints
- Block unknown destinations

**Limitations:**
- Complex to maintain allow-lists
- Doesn't prevent legitimate-looking destinations
- May break legitimate operations

### Rate Limiting

**What it is:** Limit the number of operations per time period.

**How it helps:** Prevents bulk exfiltration or destructive operations.

**Implementation:**
- API-level rate limits
- Per-token quotas
- Alerting on threshold approach

**Limitations:**
- Doesn't prevent slow exfiltration
- May impact legitimate high-volume operations
- Rate limits must be tuned to workload

### Anomaly Detection

**What it is:** Machine learning or rules-based detection of unusual access patterns.

**How it helps:** Detects compromise that other controls miss.

**Implementation:**
- Baseline normal access patterns
- Alert on deviations (new times, new profiles, unusual frequency)
- Integrate with SIEM

**Limitations:**
- Requires baseline period
- False positives require tuning
- Post-hoc detection, not prevention

---

## Scenario: Legacy System Without Guardian

You have a legacy system where agents access secrets through environment variables, and you cannot immediately implement a Guardian.

### Compensating Control Stack

| Priority | Control | Implementation |
|----------|---------|----------------|
| 1 | Short-lived credentials | Rotate environment variables every 4 hours |
| 2 | Minimal permissions | Credentials have read-only or narrow scope |
| 3 | Session limits | Agent sessions terminated after 1 hour |
| 4 | Network restrictions | Agent can only reach approved endpoints |
| 5 | Access logging | Cloud provider API logging enabled |
| 6 | Anomaly alerting | Alert on any access outside business hours |
| 7 | Rotation automation | Automated rotation of all credentials daily |

This stack significantly reduces risk while you work toward proper architectural isolation.

---

## Scenario: CI/CD Without Interactive Approval

Your CI/CD pipeline needs access to production credentials, but no human is available for interactive approval.

### Compensating Control Stack

| Priority | Control | Implementation |
|----------|---------|----------------|
| 1 | Pipeline-specific credentials | Each pipeline has its own scoped credentials |
| 2 | Time-bounded access | Credentials only valid during pipeline window |
| 3 | Pipeline attestation | Each access tagged with pipeline ID |
| 4 | Automatic rotation | Credentials rotated after each pipeline run |
| 5 | Audit integration | Pipeline logs linked to credential access logs |
| 6 | Failure alerting | Alert if pipeline accesses unexpected profiles |
| 7 | PR-based approval | Credential access requires merged PR |

---

## Scenario: Shared Service Credential Brokering

A shared service needs to use user credentials, but cannot implement the full delegation model.

### Compensating Control Stack

| Priority | Control | Implementation |
|----------|---------|----------------|
| 1 | Just-in-time access | Credentials provided at operation time only |
| 2 | No persistence | Credentials discarded immediately after use |
| 3 | User-visible audit | User can see all access by the service |
| 4 | Scope attenuation | Service receives only required fields |
| 5 | Rate limiting per-user | Each user has operation limits |
| 6 | Service identity | Service authenticated separately from user |
| 7 | User revocation | User can revoke service access at any time |

---

## When to Accept Risk

Sometimes compensating controls are insufficient. You may need to accept risk when:

1. **The risk is bounded** -- Exposure is limited to low-value credentials
2. **Detection is reliable** -- You can detect compromise quickly
3. **Recovery is fast** -- You can rotate credentials and recover in minutes
4. **The alternative is worse** -- Not having the agent at all would cause greater harm

Document accepted risks explicitly:
- What risk is accepted
- Why it's acceptable
- What would trigger re-evaluation
- Who approved the acceptance

---

## Summary

| If You Can't Implement | Stack These Controls |
|------------------------|----------------------|
| Process isolation | Short TTL + rotation + audit monitoring |
| Per-profile tokens | Service accounts + permission boundaries + rate limiting |
| Native approval dialogs | Time-bounded access + justification + audit review |
| Complete audit trail | Cloud provider logs + network logging |
| Agent isolation | No context logging + short sessions + rotation |

**Remember:** Compensating controls are not a substitute for proper architecture. They reduce risk while you work toward the ideal. The goal is always to implement the full model.

---

Next: [Anti-Patterns](appendix-c-anti-patterns.md)
